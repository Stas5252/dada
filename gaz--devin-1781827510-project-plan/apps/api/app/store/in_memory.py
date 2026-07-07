import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hmac import compare_digest
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from app.demo_data import (
    DEMO_OWNER_PASSWORD,
    build_demo_agents,
    build_demo_chat_requests,
    build_demo_knowledge_sources,
    build_demo_owner,
    build_demo_tenant,
)
from app.jobs import BackgroundJobBackend, InlineBackgroundJobBackend
from app.rag import (
    build_knowledge_chunks,
    build_qdrant_collection_contract,
    compose_grounded_answer,
    ingestion_idempotency_key,
    retrieve_sources,
    upsert_chunks_to_qdrant,
)
from app.contracts.outbound import Campaign, CampaignLead
from app.contracts.inbox import (
    ConversationTag,
    HandoffAssignment,
    InboxConversation,
    InternalNote,
)
from app.contracts.voice import VoiceSession, VoiceSessionEvent
from app.rbac import Role
from app.schemas import (
    Agent,
    AgentCreateRequest,
    AgentStatus,
    AgentUpdateRequest,
    ApiKey,
    AuditLog,
    AuthSession,
    ChatMessageRequest,
    ContactConsent,
    ContactSuppression,
    Conversation,
    ConversationStatus,
    Customer,
    KnowledgeIngestionJob,
    KnowledgeIngestionJobStatus,
    KnowledgeSource,
    KnowledgeChunk,
    KnowledgeSourceCreateRequest,
    KnowledgeSourceStatus,
    Message,
    MessageRole,
    OrderDraft,
    OrderItem,
    PasswordResetToken,
    QdrantCollectionContract,
    RegisterRequest,
    Tenant,
    TestCase,
    TestCaseCreate,
    TestCaseStatus,
    TestRun,
    User,
    VerificationToken,
)
from app.security import PasswordHash, hash_password, issue_access_token, verify_password
from app.settings import get_settings


@dataclass
class InMemoryStore:
    tenants: dict[UUID, Tenant] = field(default_factory=dict)
    users: dict[UUID, User] = field(default_factory=dict)
    agents: dict[UUID, Agent] = field(default_factory=dict)
    knowledge_sources: dict[UUID, KnowledgeSource] = field(default_factory=dict)
    knowledge_chunks: dict[str, KnowledgeChunk] = field(default_factory=dict)
    ingestion_jobs: dict[UUID, KnowledgeIngestionJob] = field(default_factory=dict)
    conversations: dict[UUID, Conversation] = field(default_factory=dict)
    messages: dict[UUID, Message] = field(default_factory=dict)
    customers: dict[UUID, Customer] = field(default_factory=dict)
    contact_suppressions: dict[UUID, ContactSuppression] = field(default_factory=dict)
    contact_consents: dict[UUID, ContactConsent] = field(default_factory=dict)
    password_hashes: dict[UUID, PasswordHash] = field(default_factory=dict)
    background_jobs: BackgroundJobBackend = field(default_factory=InlineBackgroundJobBackend)
    auth_sessions: dict[UUID, AuthSession] = field(default_factory=dict)
    verification_tokens: dict[UUID, VerificationToken] = field(default_factory=dict)
    password_reset_tokens: dict[UUID, PasswordResetToken] = field(default_factory=dict)
    audit_logs: dict[UUID, AuditLog] = field(default_factory=dict)
    api_keys: dict[UUID, ApiKey] = field(default_factory=dict)
    order_drafts: dict[UUID, OrderDraft] = field(default_factory=dict)
    test_cases: dict[UUID, TestCase] = field(default_factory=dict)
    test_runs: dict[UUID, TestRun] = field(default_factory=dict)

    def __post_init__(self) -> None:
        import sys
        settings = get_settings()
        if settings.app_env == "test" or "pytest" in sys.modules:
            self.background_jobs = InlineBackgroundJobBackend()
        else:
            from app.jobs import ArqBackgroundJobBackend
            from app.store_factory import GLOBAL_ARQ_POOL
            self.background_jobs = ArqBackgroundJobBackend(redis_pool=GLOBAL_ARQ_POOL)


    def register(
        self,
        payload: RegisterRequest,
        token_secret: str,
        access_token_ttl_minutes: int = 15,
    ) -> tuple[Tenant, User, str]:
        tenant = Tenant(name=payload.company_name)
        user = User(
            tenant_id=tenant.id,
            email=payload.owner_email,
            name=payload.owner_name,
            email_verified=False,
        )
        self.tenants[tenant.id] = tenant
        self.users[user.id] = user
        self.password_hashes[user.id] = hash_password(payload.password)
        token = issue_access_token(
            tenant.id,
            user.id,
            token_secret,
            ttl_minutes=access_token_ttl_minutes,
        )
        return tenant, user, token

    def login(
        self,
        email: str,
        password: str,
        token_secret: str,
        access_token_ttl_minutes: int = 15,
    ) -> tuple[Tenant, User, str] | None:
        user = next(
            (candidate for candidate in self.users.values() if candidate.email == email),
            None,
        )
        if not user:
            return None
        password_hash = self.password_hashes.get(user.id)
        if not password_hash or not verify_password(password, password_hash):
            return None
        tenant = self.tenants.get(user.tenant_id)
        if not tenant:
            return None
        token: str | None = None
        if not user.totp_secret:
            token = issue_access_token(
                tenant.id,
                user.id,
                token_secret,
                ttl_minutes=access_token_ttl_minutes,
            )
        return tenant, user, token or "".join(())

    def create_auth_session(
        self,
        session_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> AuthSession:
        session = AuthSession(
            id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
        )
        self.auth_sessions[session.id] = session
        return session

    def rotate_auth_session(
        self,
        session_id: UUID,
        presented_refresh_token_hash: str,
        new_session_id: UUID,
        new_refresh_token_hash: str,
        new_expires_at: datetime,
    ) -> AuthSession | None:
        current_session = self.auth_sessions.get(session_id)
        now = datetime.now(UTC)
        if not _is_refresh_session_usable(
            current_session,
            presented_refresh_token_hash,
            now,
        ):
            return None
        if current_session is None:
            return None
        new_session = AuthSession(
            id=new_session_id,
            tenant_id=current_session.tenant_id,
            user_id=current_session.user_id,
            refresh_token_hash=new_refresh_token_hash,
            expires_at=new_expires_at,
        )
        self.auth_sessions[current_session.id] = current_session.model_copy(
            update={
                "revoked_at": now,
                "replaced_by_session_id": new_session.id,
                "updated_at": now,
            }
        )
        self.auth_sessions[new_session.id] = new_session
        return new_session

    def revoke_auth_session(
        self,
        session_id: UUID,
        presented_refresh_token_hash: str,
    ) -> bool:
        current_session = self.auth_sessions.get(session_id)
        now = datetime.now(UTC)
        if not _is_refresh_session_usable(
            current_session,
            presented_refresh_token_hash,
            now,
        ):
            return False
        if current_session is None:
            return False
        self.auth_sessions[current_session.id] = current_session.model_copy(
            update={"revoked_at": now, "updated_at": now}
        )
        return True

    def list_all_tenants(self) -> list[Tenant]:
        return list(self.tenants.values())

    def get_tenant(self, tenant_id: UUID) -> Tenant | None:
        return self.tenants.get(tenant_id)

    def update_tenant_settings(self, tenant_id: UUID, settings: dict[str, object]) -> Tenant | None:
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        updated_settings = {**tenant.settings, **settings}
        updated_tenant = tenant.model_copy(update={"settings": updated_settings})
        self.tenants[tenant_id] = updated_tenant
        return updated_tenant

    def evaluate_test_case(self, tenant_id: UUID, test_case_id: str) -> dict[str, Any]:
        """Evaluate a test case using RAG metrics."""
        raise NotImplementedError

    # Inbox & Handoff
    def list_inbox_conversations(
        self,
        tenant_id: UUID,
        handoff_status: str | None = None,
        assigned_user_id: str | None = None
    ) -> list[InboxConversation]:
        """List conversations for the human handoff inbox."""
        raise NotImplementedError

    def assign_conversation(
        self, tenant_id: UUID, conversation_id: str, user_id: str
    ) -> InboxConversation | None:
        """Assign a conversation to a human manager."""
        raise NotImplementedError

    def return_conversation_to_ai(
        self, tenant_id: UUID, conversation_id: str
    ) -> InboxConversation | None:
        """Return a conversation to AI handling."""
        raise NotImplementedError

    def add_conversation_tag(
        self, tenant_id: UUID, conversation_id: str, tag_name: str
    ) -> ConversationTag | None:
        """Add a tag to a conversation."""
        raise NotImplementedError

    def remove_conversation_tag(
        self, tenant_id: UUID, conversation_id: str, tag_name: str
    ) -> bool:
        """Remove a tag from a conversation."""
        raise NotImplementedError

    def add_internal_note(
        self, tenant_id: UUID, conversation_id: str, body: str, author_user_id: str | None = None
    ) -> InternalNote | None:
        """Add an internal note to a conversation."""
        raise NotImplementedError

    def get_analytics_overview(self, tenant_id: UUID) -> dict[str, Any]:
        """Fetch optimized analytics overview directly via SQL."""
        raise NotImplementedError

    def save_qa_evaluation(self, evaluation: Any) -> None:
        """Save QA evaluation for a conversation."""
        raise NotImplementedError

    def get_qa_evaluations(self, tenant_id: UUID, conversation_id: UUID) -> list[Any]:
        """Get QA evaluations for a conversation."""
        raise NotImplementedError

    def save_weekly_report(self, report: Any) -> None:
        """Save weekly report."""
        raise NotImplementedError

    def list_weekly_reports(self, tenant_id: UUID) -> list[Any]:
        """List weekly reports."""
        raise NotImplementedError

    def update_tenant_plan(self, tenant_id: UUID, plan: str) -> Tenant | None:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        tenant.plan = plan
        updated_tenant = tenant.model_copy(update={"plan": plan})
        self.tenants[tenant_id] = updated_tenant
        return updated_tenant

    def get_user(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        return next(
            (candidate for candidate in self.users.values() if candidate.email == email), None
        )

    def create_verification_token(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> VerificationToken:
        token = VerificationToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.verification_tokens[token.id] = token
        return token

    def consume_verification_token(
        self, token_hash: str, now: datetime
    ) -> VerificationToken | None:
        token = next(
            (t for t in self.verification_tokens.values() if t.token_hash == token_hash), None
        )
        if not token or token.used_at or token.expires_at <= now:
            return None
        token.used_at = now
        self.verification_tokens[token.id] = token
        return token

    def verify_user_email(self, user_id: UUID) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        user.email_verified = True
        return True

    def create_password_reset_token(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        token = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.password_reset_tokens[token.id] = token
        return token

    def consume_password_reset_token(
        self, token_hash: str, now: datetime
    ) -> PasswordResetToken | None:
        token = next(
            (t for t in self.password_reset_tokens.values() if t.token_hash == token_hash), None
        )
        if not token or token.used_at or token.expires_at <= now:
            return None
        token.used_at = now
        self.password_reset_tokens[token.id] = token
        return token

    def update_user_password(self, user_id: UUID, password_hash: PasswordHash) -> bool:
        if user_id not in self.users:
            return False
        self.password_hashes[user_id] = password_hash
        return True

    def update_user_mfa(
        self,
        user_id: UUID,
        totp_secret: str | None,
        recovery_code_hashes: list[str] | None = None,
    ) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        updates: dict[str, object] = {
            "totp_secret": totp_secret,
            "updated_at": datetime.now(UTC),
        }
        if recovery_code_hashes is not None:
            updates["mfa_recovery_code_hashes"] = recovery_code_hashes
        self.users[user_id] = user.model_copy(update=updates)
        return True

    def replace_mfa_recovery_code_hashes(self, user_id: UUID, code_hashes: list[str]) -> bool:
        user = self.users.get(user_id)
        if not user or not user.totp_secret:
            return False
        self.users[user_id] = user.model_copy(
            update={
                "mfa_recovery_code_hashes": code_hashes,
                "updated_at": datetime.now(UTC),
            }
        )
        return True

    def consume_mfa_recovery_code(self, user_id: UUID, code_hash: str) -> bool:
        user = self.users.get(user_id)
        if not user or not user.totp_secret:
            return False
        remaining = [
            stored_hash
            for stored_hash in user.mfa_recovery_code_hashes
            if not compare_digest(stored_hash, code_hash)
        ]
        if len(remaining) == len(user.mfa_recovery_code_hashes):
            return False
        self.users[user_id] = user.model_copy(
            update={
                "mfa_recovery_code_hashes": remaining,
                "updated_at": datetime.now(UTC),
            }
        )
        return True

    def create_audit_log(
        self,
        event_type: str,
        user_id: UUID | None = None,
        tenant_id: UUID | None = None,
        ip_address: str | None = None,
        details: dict[str, str] | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            event_type=event_type,
            user_id=user_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            details=details or {},
        )
        self.audit_logs[audit_log.id] = audit_log
        return audit_log

    def list_audit_logs(self, tenant_id: UUID) -> list[AuditLog]:
        logs = [log for log in self.audit_logs.values() if log.tenant_id == tenant_id]
        return sorted(logs, key=lambda x: x.created_at, reverse=True)

    def create_agent(self, tenant_id: UUID, payload: AgentCreateRequest) -> Agent:
        agent = Agent(
            tenant_id=tenant_id,
            name=payload.name,
            prompt=payload.prompt,
            channel=payload.channel,
            voice_id=payload.voice_id,
            voice_language=payload.voice_language,
            voice_speed=payload.voice_speed,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            model_name=payload.model_name,
            pathway_nodes=payload.pathway_nodes,
            pathway_edges=payload.pathway_edges,
            business_profile=payload.business_profile,
            agent_role=payload.agent_role,
            agent_tone=payload.agent_tone,
            agent_language=payload.agent_language,
            business_hours=payload.business_hours,
            escalation_rules=payload.escalation_rules,
            sales_rules=payload.sales_rules,
            forbidden_topics=payload.forbidden_topics,
            enabled_tools=payload.enabled_tools,
        )
        self.agents[agent.id] = agent
        return agent

    def get_agent(self, tenant_id: UUID, agent_id: UUID) -> Agent | None:
        agent = self.agents.get(agent_id)
        if not agent or agent.tenant_id != tenant_id:
            return None
        return agent

    def list_agents(self, tenant_id: UUID) -> list[Agent]:
        return [agent for agent in self.agents.values() if agent.tenant_id == tenant_id]

    def update_agent(
        self,
        tenant_id: UUID,
        agent_id: UUID,
        payload: AgentUpdateRequest,
    ) -> Agent | None:
        agent = self.get_agent(tenant_id, agent_id)
        if agent is None:
            return None

        updates: dict[str, object] = {}
        requires_republish = False

        if payload.name is not None and payload.name != agent.name:
            updates["name"] = payload.name
        if payload.prompt is not None and payload.prompt != agent.prompt:
            updates["prompt"] = payload.prompt
            requires_republish = True
        if payload.channel is not None and payload.channel != agent.channel:
            updates["channel"] = payload.channel
            requires_republish = True
        if payload.voice_id is not None and payload.voice_id != agent.voice_id:
            updates["voice_id"] = payload.voice_id
        if payload.voice_language is not None and payload.voice_language != agent.voice_language:
            updates["voice_language"] = payload.voice_language
        if payload.voice_speed is not None and payload.voice_speed != agent.voice_speed:
            updates["voice_speed"] = payload.voice_speed
        if payload.temperature is not None and payload.temperature != agent.temperature:
            updates["temperature"] = payload.temperature
        if payload.max_tokens is not None and payload.max_tokens != agent.max_tokens:
            updates["max_tokens"] = payload.max_tokens
        if payload.model_name is not None and payload.model_name != agent.model_name:
            updates["model_name"] = payload.model_name
        if payload.telegram_bot_token is not None and payload.telegram_bot_token != agent.telegram_bot_token:
            updates["telegram_bot_token"] = payload.telegram_bot_token
        if payload.pathway_nodes is not None and payload.pathway_nodes != agent.pathway_nodes:
            updates["pathway_nodes"] = payload.pathway_nodes
        if payload.pathway_edges is not None and payload.pathway_edges != agent.pathway_edges:
            updates["pathway_edges"] = payload.pathway_edges
        if (
            payload.business_profile is not None
            and payload.business_profile != agent.business_profile
        ):
            updates["business_profile"] = payload.business_profile
            requires_republish = True
        if payload.agent_role is not None and payload.agent_role != agent.agent_role:
            updates["agent_role"] = payload.agent_role
            requires_republish = True
        if payload.agent_tone is not None and payload.agent_tone != agent.agent_tone:
            updates["agent_tone"] = payload.agent_tone
            requires_republish = True
        if payload.agent_language is not None and payload.agent_language != agent.agent_language:
            updates["agent_language"] = payload.agent_language
            requires_republish = True
        if payload.business_hours is not None and payload.business_hours != agent.business_hours:
            updates["business_hours"] = payload.business_hours
            requires_republish = True
        if (
            payload.escalation_rules is not None
            and payload.escalation_rules != agent.escalation_rules
        ):
            updates["escalation_rules"] = payload.escalation_rules
            requires_republish = True
        if payload.sales_rules is not None and payload.sales_rules != agent.sales_rules:
            updates["sales_rules"] = payload.sales_rules
            requires_republish = True
        if (
            payload.forbidden_topics is not None
            and payload.forbidden_topics != agent.forbidden_topics
        ):
            updates["forbidden_topics"] = payload.forbidden_topics
            requires_republish = True
        if payload.enabled_tools is not None and payload.enabled_tools != agent.enabled_tools:
            updates["enabled_tools"] = payload.enabled_tools
            requires_republish = True

        if updates:
            updates["version"] = agent.version + 1
            updates["updated_at"] = datetime.now(UTC)
            if requires_republish:
                updates["status"] = AgentStatus.draft
            agent = agent.model_copy(update=updates)
            self.agents[agent.id] = agent

        return agent

    def publish_agent(self, tenant_id: UUID, agent_id: UUID) -> Agent | None:
        agent = self.agents.get(agent_id)
        if not agent or agent.tenant_id != tenant_id:
            return None
        published_agent = agent.model_copy(
            update={"status": AgentStatus.published, "updated_at": datetime.now(UTC)}
        )
        self.agents[agent_id] = published_agent
        return published_agent

    def create_knowledge_source(
        self,
        tenant_id: UUID,
        payload: KnowledgeSourceCreateRequest,
    ) -> KnowledgeSource:
        source = KnowledgeSource(
            tenant_id=tenant_id,
            title=payload.title,
            source_type=payload.source_type,
            content=payload.content,
            status=KnowledgeSourceStatus.pending,
            chunk_count=0,
        )
        self.knowledge_sources[source.id] = source
        self.enqueue_knowledge_ingestion(tenant_id, source.id)
        return self.knowledge_sources[source.id]

    def list_knowledge_sources(self, tenant_id: UUID) -> list[KnowledgeSource]:
        return [
            source for source in self.knowledge_sources.values() if source.tenant_id == tenant_id
        ]

    def get_knowledge_source(
        self, tenant_id: UUID, source_id: UUID
    ) -> KnowledgeSource | None:
        source = self.knowledge_sources.get(source_id)
        if source is None or source.tenant_id != tenant_id:
            return None
        return source

    def qdrant_collection_contract(self) -> QdrantCollectionContract:
        settings = get_settings()
        return build_qdrant_collection_contract(
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
            distance=settings.qdrant_distance,
        )

    def list_ingestion_jobs(self, tenant_id: UUID) -> list[KnowledgeIngestionJob]:
        return [job for job in self.ingestion_jobs.values() if job.tenant_id == tenant_id]

    def get_ingestion_job(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> KnowledgeIngestionJob | None:
        job = self.ingestion_jobs.get(job_id)
        if not job or job.tenant_id != tenant_id:
            return None
        return job

    def enqueue_knowledge_ingestion(
        self,
        tenant_id: UUID,
        source_id: UUID,
    ) -> KnowledgeIngestionJob | None:
        source = self.knowledge_sources.get(source_id)
        if not source or source.tenant_id != tenant_id:
            return None
        contract = self.qdrant_collection_contract()
        idempotency_key = ingestion_idempotency_key(source)
        job_id = uuid5(NAMESPACE_URL, idempotency_key)
        for existing_job in self.ingestion_jobs.values():
            if existing_job.idempotency_key == idempotency_key:
                return existing_job
        job = KnowledgeIngestionJob(
            id=job_id,
            tenant_id=tenant_id,
            source_id=source.id,
            idempotency_key=idempotency_key,
            qdrant_collection=contract.collection_name,
            background_backend=self.background_jobs.backend_name,
        )
        self.ingestion_jobs[job.id] = job
        self.background_jobs.submit('run_knowledge_ingestion', job.id, _store=self)
        return self.ingestion_jobs[job.id]

    def run_knowledge_ingestion(self, job_id: UUID) -> None:
        job = self.ingestion_jobs[job_id]
        self.ingestion_jobs[job.id] = job.model_copy(
            update={
                "status": KnowledgeIngestionJobStatus.running,
                "updated_at": datetime.now(UTC),
            }
        )
        job = self.ingestion_jobs[job.id]
        source = self.knowledge_sources[job.source_id]
        try:
            settings = get_settings()
            chunks = build_knowledge_chunks(source, vector_size=settings.qdrant_vector_size)
            for chunk in chunks:
                self.knowledge_chunks[chunk.id] = chunk
            upsert_chunks_to_qdrant(chunks, job.qdrant_collection)
            self.knowledge_sources[source.id] = source.model_copy(
                update={
                    "status": KnowledgeSourceStatus.indexed,
                    "chunk_count": len(chunks),
                    "updated_at": datetime.now(UTC),
                }
            )
            self.ingestion_jobs[job.id] = job.model_copy(
                update={
                    "status": KnowledgeIngestionJobStatus.completed,
                    "chunk_count": len(chunks),
                    "updated_at": datetime.now(UTC),
                }
            )
        except Exception as exc:
            import traceback

            traceback.print_exc()
            with open("ingestion_error.txt", "w") as f:
                f.write(str(exc) + "\n" + traceback.format_exc())
            self.knowledge_sources[source.id] = source.model_copy(
                update={
                    "status": KnowledgeSourceStatus.failed,
                    "updated_at": datetime.now(UTC),
                }
            )
            self.ingestion_jobs[job.id] = job.model_copy(
                update={
                    "status": KnowledgeIngestionJobStatus.failed,
                    "error_message": str(exc),
                    "updated_at": datetime.now(UTC),
                }
            )
            raise exc

    def list_conversations(
        self,
        tenant_id: UUID,
        search: str | None = None,
        status: str | None = None,
        channel: str | None = None,
    ) -> list[Conversation]:
        res = [
            conversation
            for conversation in self.conversations.values()
            if conversation.tenant_id == tenant_id
        ]
        if status:
            res = [c for c in res if c.status.value == status]
        if channel:
            res = [c for c in res if c.channel.lower() == channel.lower()]
        if search:
            search_lower = search.lower()
            res = [c for c in res if search_lower in c.summary.lower()]
        return res

    def get_conversation_detail(
        self, tenant_id: UUID, conversation_id: UUID
    ) -> (
        tuple[
            Conversation,
            list[Message],
            list[KnowledgeSource],
        ]
        | None
    ):
        conversation = self.conversations.get(conversation_id)
        if not conversation or conversation.tenant_id != tenant_id:
            return None
        messages = [
            message
            for message in self.messages.values()
            if message.tenant_id == tenant_id and message.conversation_id == conversation_id
        ]
        source_ids = {source_id for message in messages for source_id in message.source_ids}
        sources = [
            source
            for source in self.knowledge_sources.values()
            if source.tenant_id == tenant_id and source.id in source_ids
        ]
        return conversation, messages, sources

    def get_conversation(self, tenant_id: UUID, conversation_id: UUID) -> Conversation | None:
        conversation = self.conversations.get(conversation_id)
        if not conversation or conversation.tenant_id != tenant_id:
            return None
        return conversation

    def add_operator_message(
        self, tenant_id: UUID, conversation_id: UUID, content: str
    ) -> Message | None:
        conversation = self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            return None

        message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.operator,
            content=content,
            source_ids=[],
        )
        self.messages[message.id] = message

        self.conversations[conversation_id] = conversation.model_copy(
            update={"updated_at": datetime.now(UTC)}
        )
        return message

    def run_agent_workflow(
        self, tenant_id: UUID, task_payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        pass

    #
    # Outbound Campaigns
    #
    def create_campaign(self, tenant_id: UUID, name: str, agent_id: str, max_attempts: int, retry_delay_minutes: int) -> 'Campaign':
        pass

    def get_campaign(self, tenant_id: UUID, campaign_id: str) -> 'Campaign | None':
        pass

    def list_campaigns(self, tenant_id: UUID) -> list['Campaign']:
        pass

    def update_campaign_status(self, tenant_id: UUID, campaign_id: str, status: str) -> 'Campaign | None':
        pass

    def add_campaign_lead(self, tenant_id: UUID, campaign_id: str, phone: str, variables: dict[str, Any]) -> 'CampaignLead':
        pass

    def list_campaign_leads(self, tenant_id: UUID, campaign_id: str) -> list['CampaignLead']:
        pass

    def update_campaign_lead(self, tenant_id: UUID, lead_id: str, status: str | None = None, outcome: str | None = None, increment_attempt: bool = False) -> 'CampaignLead | None':
        pass

    def get_due_campaign_leads(self) -> list['CampaignLead']:
        pass

    def resolve_conversation(
        self, tenant_id: UUID, conversation_id: UUID
    ) -> Conversation | None:
        conversation = self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            return None

        updated = conversation.model_copy(
            update={
                "status": ConversationStatus.resolved,
                "resolution_status": "Resolved by operator",
                "updated_at": datetime.now(UTC),
            }
        )
        self.conversations[conversation_id] = updated
        return updated

    def escalate_conversation(
        self, tenant_id: UUID, conversation_id: UUID
    ) -> Conversation | None:
        conversation = self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            return None

        updated = conversation.model_copy(
            update={
                "status": ConversationStatus.escalated,
                "resolution_status": "Escalated to human operator",
                "updated_at": datetime.now(UTC),
            }
        )
        self.conversations[conversation_id] = updated
        return updated

    def update_conversation_summary(
        self, tenant_id: UUID, conversation_id: UUID, summary: str
    ) -> Conversation | None:
        conversation = self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            return None

        updated = conversation.model_copy(
            update={
                "summary": summary,
                "updated_at": datetime.now(UTC),
            }
        )
        self.conversations[conversation_id] = updated
        return updated

    def get_customer(self, tenant_id: UUID, customer_id: UUID) -> Customer | None:
        customer = self.customers.get(customer_id)
        if not customer or customer.tenant_id != tenant_id:
            return None
        return customer

    def get_customer_by_external_id(
        self, tenant_id: UUID, channel: str, external_id: str
    ) -> Customer | None:
        return next(
            (
                c
                for c in self.customers.values()
                if c.tenant_id == tenant_id
                and c.channel == channel
                and c.external_id == external_id
            ),
            None,
        )

    def create_customer(
        self,
        tenant_id: UUID,
        channel: str,
        external_id: str,
        name: str | None = None,
        phone: str | None = None,
    ) -> Customer:
        customer = Customer(
            tenant_id=tenant_id,
            channel=channel,
            external_id=external_id,
            name=name,
            phone=phone,
        )
        self.customers[customer.id] = customer
        return customer

    def update_customer(
        self,
        tenant_id: UUID,
        customer_id: UUID,
        name: str | None = None,
        phone: str | None = None,
        tags: list[str] | None = None,
    ) -> Customer | None:
        customer = self.customers.get(customer_id)
        if not customer or customer.tenant_id != tenant_id:
            return None
        updates: dict[str, object] = {"updated_at": datetime.now(UTC)}
        if name is not None:
            updates["name"] = name
        if phone is not None:
            updates["phone"] = phone
        if tags is not None:
            updates["tags"] = tags
        customer = customer.model_copy(update=updates)
        self.customers[customer.id] = customer
        return customer

    def record_contact_suppression(
        self,
        tenant_id: UUID,
        channel: str,
        contact_type: str,
        value: str,
        reason: str = "opt_out_requested",
        source: str = "runtime_guardrail",
    ) -> ContactSuppression:
        normalized_type = _normalize_suppression_contact_type(contact_type)
        normalized_channel = _normalize_suppression_channel(channel, normalized_type)
        normalized_value = _normalize_suppression_value(normalized_type, value)

        existing = self.find_contact_suppression(
            tenant_id,
            normalized_channel,
            contact_type=normalized_type,
            value=normalized_value,
            include_revoked=True,
        )
        now = datetime.now(UTC)
        if existing:
            suppression = existing.model_copy(
                update={
                    "reason": reason,
                    "source": source,
                    "status": "active",
                    "updated_at": now,
                }
            )
            self.contact_suppressions[suppression.id] = suppression
        else:
            suppression = ContactSuppression(
                tenant_id=tenant_id,
                channel=normalized_channel,
                contact_type=normalized_type,
                value=normalized_value,
                reason=reason,
                source=source,
                status="active",
            )
            self.contact_suppressions[suppression.id] = suppression

        self.create_audit_log(
            event_type="contact_suppression.recorded",
            tenant_id=tenant_id,
            details={
                "channel": suppression.channel,
                "contact_type": suppression.contact_type,
                "reason": suppression.reason,
                "source": suppression.source,
                "status": suppression.status,
                "value": suppression.value,
            },
        )
        return suppression

    def find_contact_suppression(
        self,
        tenant_id: UUID,
        channel: str,
        *,
        external_id: str | None = None,
        phone: str | None = None,
        contact_type: str | None = None,
        value: str | None = None,
        include_revoked: bool = False,
    ) -> ContactSuppression | None:
        candidates: list[tuple[str, str, str]] = []
        if contact_type and value:
            normalized_type = _normalize_suppression_contact_type(contact_type)
            candidates.append(
                (
                    _normalize_suppression_channel(channel, normalized_type),
                    normalized_type,
                    _normalize_suppression_value(normalized_type, value),
                )
            )
        if external_id:
            candidates.append(
                (
                    _normalize_suppression_channel(channel, "external_id"),
                    "external_id",
                    _normalize_suppression_value("external_id", external_id),
                )
            )
            if _looks_like_phone(external_id):
                candidates.append(
                    (
                        "*",
                        "phone",
                        _normalize_suppression_value("phone", external_id),
                    )
                )
        if phone:
            try:
                normalized_phone = _normalize_suppression_value("phone", phone)
            except ValueError:
                normalized_phone = None
            if normalized_phone:
                candidates.append(("*", "phone", normalized_phone))
                candidates.append(
                    (
                        _normalize_suppression_channel(channel, "phone"),
                        "phone",
                        normalized_phone,
                    )
                )

        for suppression in self.contact_suppressions.values():
            if suppression.tenant_id != tenant_id:
                continue
            if not include_revoked and suppression.status != "active":
                continue
            if (suppression.channel, suppression.contact_type, suppression.value) in candidates:
                return suppression
        return None

    def list_contact_suppressions(self, tenant_id: UUID) -> list[ContactSuppression]:
        suppressions = [
            suppression
            for suppression in self.contact_suppressions.values()
            if suppression.tenant_id == tenant_id
        ]
        return sorted(suppressions, key=lambda item: item.updated_at, reverse=True)

    def revoke_contact_suppression(
        self,
        tenant_id: UUID,
        suppression_id: UUID,
    ) -> ContactSuppression | None:
        suppression = self.contact_suppressions.get(suppression_id)
        if not suppression or suppression.tenant_id != tenant_id:
            return None
        updated = suppression.model_copy(
            update={"status": "revoked", "updated_at": datetime.now(UTC)}
        )
        self.contact_suppressions[updated.id] = updated
        self.create_audit_log(
            event_type="contact_suppression.revoked",
            tenant_id=tenant_id,
            details={
                "channel": updated.channel,
                "contact_type": updated.contact_type,
                "status": updated.status,
                "value": updated.value,
            },
        )
        return updated

    def record_contact_consent(
        self,
        tenant_id: UUID,
        channel: str,
        contact_type: str,
        value: str,
        consent_type: str = "outbound_contact",
        source: str = "manual",
        expires_at: datetime | None = None,
    ) -> ContactConsent:
        normalized_type = _normalize_suppression_contact_type(contact_type)
        normalized_channel = _normalize_suppression_channel(channel, normalized_type)
        normalized_value = _normalize_suppression_value(normalized_type, value)
        normalized_consent_type = _normalize_consent_type(consent_type)

        existing = self.find_contact_consent(
            tenant_id,
            normalized_channel,
            contact_type=normalized_type,
            value=normalized_value,
            consent_type=normalized_consent_type,
            include_revoked=True,
        )
        now = datetime.now(UTC)
        if existing:
            consent = existing.model_copy(
                update={
                    "source": source,
                    "status": "active",
                    "expires_at": expires_at,
                    "updated_at": now,
                }
            )
            self.contact_consents[consent.id] = consent
        else:
            consent = ContactConsent(
                tenant_id=tenant_id,
                channel=normalized_channel,
                contact_type=normalized_type,
                value=normalized_value,
                consent_type=normalized_consent_type,
                source=source,
                status="active",
                expires_at=expires_at,
            )
            self.contact_consents[consent.id] = consent

        self.create_audit_log(
            event_type="contact_consent.recorded",
            tenant_id=tenant_id,
            details={
                "channel": consent.channel,
                "consent_type": consent.consent_type,
                "contact_type": consent.contact_type,
                "source": consent.source,
                "status": consent.status,
                "value": consent.value,
            },
        )
        return consent

    def find_contact_consent(
        self,
        tenant_id: UUID,
        channel: str,
        *,
        external_id: str | None = None,
        phone: str | None = None,
        contact_type: str | None = None,
        value: str | None = None,
        consent_type: str = "outbound_contact",
        include_revoked: bool = False,
    ) -> ContactConsent | None:
        candidates = _contact_lookup_candidates(
            channel,
            external_id=external_id,
            phone=phone,
            contact_type=contact_type,
            value=value,
        )
        normalized_consent_type = _normalize_consent_type(consent_type)
        now = datetime.now(UTC)

        for consent in self.contact_consents.values():
            if consent.tenant_id != tenant_id:
                continue
            if consent.consent_type != normalized_consent_type:
                continue
            if not include_revoked and not _is_contact_consent_active(consent, now):
                continue
            if (consent.channel, consent.contact_type, consent.value) in candidates:
                return consent
        return None

    def list_contact_consents(self, tenant_id: UUID) -> list[ContactConsent]:
        consents = [
            consent
            for consent in self.contact_consents.values()
            if consent.tenant_id == tenant_id
        ]
        return sorted(consents, key=lambda item: item.updated_at, reverse=True)

    def revoke_contact_consent(
        self,
        tenant_id: UUID,
        consent_id: UUID,
    ) -> ContactConsent | None:
        consent = self.contact_consents.get(consent_id)
        if not consent or consent.tenant_id != tenant_id:
            return None
        updated = consent.model_copy(
            update={"status": "revoked", "updated_at": datetime.now(UTC)}
        )
        self.contact_consents[updated.id] = updated
        self.create_audit_log(
            event_type="contact_consent.revoked",
            tenant_id=tenant_id,
            details={
                "channel": updated.channel,
                "consent_type": updated.consent_type,
                "contact_type": updated.contact_type,
                "status": updated.status,
                "value": updated.value,
            },
        )
        return updated

    def count_messages(self, tenant_id: UUID, since: datetime | None = None) -> int:
        return sum(
            1 for m in self.messages.values()
            if m.tenant_id == tenant_id and (since is None or m.created_at >= since)
        )

    def answer_chat(
        self, tenant_id: UUID, payload: ChatMessageRequest, agent_response_text: str | None = None,
        confidence_score: float | None = None,
        forced_status: ConversationStatus | None = None,
        forced_resolution_status: str | None = None,
    ) -> (
        tuple[
            Conversation,
            Message,
            Message,
            list[KnowledgeSource],
        ]
        | None
    ):
        return self.record_chat_turn(
            tenant_id=tenant_id,
            agent_id=payload.agent_id,
            conversation_id=payload.conversation_id or uuid4(),
            channel=payload.channel,
            customer_text=payload.message,
            agent_response_text=agent_response_text,
            customer_id=None,
            confidence_score=confidence_score,
            forced_status=forced_status,
            forced_resolution_status=forced_resolution_status,
        )

    def record_chat_turn(
        self,
        tenant_id: UUID,
        agent_id: UUID,
        conversation_id: UUID,
        channel: str,
        customer_text: str,
        agent_response_text: str | None = None,
        customer_id: UUID | None = None,
        confidence_score: float | None = None,
        forced_status: ConversationStatus | None = None,
        forced_resolution_status: str | None = None,
        retrieval_results: list[Any] | None = None,
    ) -> tuple[Conversation, Message, Message, list[KnowledgeSource]] | None:
        agent = self.agents.get(agent_id)
        if not agent or agent.tenant_id != tenant_id:
            return None

        # Visual Pathway Graph interpretation fallback
        if agent_response_text is None:
            previous_messages = [m for m in self.messages.values() if m.conversation_id == conversation_id]
            from app.scenario_engine import interpret_pathway
            pathway_response = interpret_pathway(agent, previous_messages, customer_text)
            if pathway_response:
                agent_response_text = pathway_response

        payload = ChatMessageRequest(agent_id=agent_id, channel=channel, message=customer_text)
        sources = self.list_knowledge_sources(tenant_id)
        settings = get_settings()
        retrieval_results = retrieve_sources(
            tenant_id=tenant_id,
            query=customer_text,
            collection_name=settings.qdrant_collection_name,
            vector_size=settings.qdrant_vector_size,
            limit=1,
        )
        selected_result = retrieval_results[0] if retrieval_results else None
        selected_source = (
            next((source for source in sources if source.id == selected_result.source_id), None)
            if selected_result
            else None
        )
        source_ids = [selected_source.id] if selected_source else []
        status_value = (
            ConversationStatus.resolved if selected_source else ConversationStatus.escalated
        )
        resolution_status = "resolved" if selected_source else "needs_human"
        if forced_status is not None:
            status_value = forced_status
        if forced_resolution_status is not None:
            resolution_status = forced_resolution_status
        conversation = self.conversations.get(conversation_id)
        if conversation:
            if conversation.tenant_id != tenant_id or conversation.agent_id != agent_id:
                return None
            conversation = conversation.model_copy(
                update={
                    "channel": channel,
                    "status": status_value,
                    "summary": conversation.summary or customer_text[:120],
                    "resolution_status": resolution_status,
                    "updated_at": datetime.now(UTC),
                }
            )
        else:
            conversation = Conversation(
                id=conversation_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                customer_id=customer_id,
                channel=channel,
                status=status_value,
                summary=customer_text[:120],
                resolution_status=resolution_status,
            )

        customer_message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            role=MessageRole.customer,
            content=customer_text,
        )
        agent_message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            role=MessageRole.agent,
            content=agent_response_text
            if agent_response_text
            else compose_grounded_answer(payload.message, selected_result),
            confidence=confidence_score if confidence_score is not None else (0.86 if selected_source else 0.2),
            source_ids=source_ids,
        )
        self.conversations[conversation.id] = conversation
        self.messages[customer_message.id] = customer_message
        self.messages[agent_message.id] = agent_message
        selected_sources = [selected_source] if selected_source else []
        return conversation, customer_message, agent_message, selected_sources

    def seed_demo_data(
        self,
        tenant_id: UUID,
        token_secret: str,
    ) -> Tenant:
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            tenant = build_demo_tenant(tenant_id)
            self.tenants[tenant.id] = tenant

        owner = build_demo_owner(tenant.id)
        if owner.id not in self.users:
            self.users[owner.id] = owner
            self.password_hashes[owner.id] = hash_password(DEMO_OWNER_PASSWORD)

        for agent in build_demo_agents(tenant.id):
            self.agents.setdefault(agent.id, agent)

        for source in build_demo_knowledge_sources(tenant.id):
            self.knowledge_sources.setdefault(source.id, source)
            self.enqueue_knowledge_ingestion(tenant.id, source.id)

        if not self.list_conversations(tenant.id):
            primary_agent = build_demo_agents(tenant.id)[0]
            for chat_request in build_demo_chat_requests(primary_agent.id):
                self.answer_chat(tenant.id, chat_request)

        issue_access_token(tenant.id, owner.id, token_secret)
        return tenant

    def list_tenant_users(self, tenant_id: UUID) -> list[User]:
        return [user for user in self.users.values() if user.tenant_id == tenant_id]

    def create_tenant_user(self, user: User, password: str) -> None:
        self.users[user.id] = user
        self.password_hashes[user.id] = hash_password(password)

    def update_user_role(self, tenant_id: UUID, user_id: UUID, role: Role) -> User | None:
        user = self.users.get(user_id)
        if not user or user.tenant_id != tenant_id:
            return None
        updated = user.model_copy(update={"role": role, "updated_at": datetime.now(UTC)})
        self.users[user.id] = updated
        return updated

    def remove_tenant_user(self, tenant_id: UUID, user_id: UUID) -> None:
        user = self.users.get(user_id)
        if user and user.tenant_id == tenant_id:
            self.users.pop(user_id, None)
            self.password_hashes.pop(user_id, None)

    def create_api_key(
        self,
        tenant_id: UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        created_by: UUID,
        scopes: list[str],
    ) -> ApiKey:
        key = ApiKey(
            id=uuid5(NAMESPACE_URL, key_hash),
            tenant_id=tenant_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            created_by=created_by,
            scopes=scopes,
            created_at=datetime.now(UTC),
        )
        self.api_keys[key.id] = key
        return key

    def list_api_keys(self, tenant_id: UUID) -> list[ApiKey]:
        return [candidate for candidate in self.api_keys.values() if candidate.tenant_id == tenant_id]

    def get_order_draft(self, tenant_id: UUID, conversation_id: UUID) -> OrderDraft | None:
        for draft in self.order_drafts.values():
            if draft.tenant_id == tenant_id and draft.conversation_id == conversation_id:
                return draft
        return None

    def add_order_item(
        self, tenant_id: UUID, conversation_id: UUID, product_name: str, quantity: int, price_per_unit: int, product_external_id: str | None = None
    ) -> OrderDraft:
        draft = self.get_order_draft(tenant_id, conversation_id)
        now = datetime.now(UTC)
        if not draft:
            draft = OrderDraft(
                id=uuid4(),
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                status="draft",
                total_amount=0,
                created_at=now,
                updated_at=now,
                items=[],
            )
            self.order_drafts[draft.id] = draft
        
        existing_item = next((i for i in draft.items if i.product_name == product_name), None)
        if existing_item:
            existing_item.quantity += quantity
        else:
            draft.items.append(
                OrderItem(
                    id=uuid4(),
                    order_id=draft.id,
                    product_name=product_name,
                    product_external_id=product_external_id,
                    quantity=quantity,
                    price_per_unit=price_per_unit,
                    created_at=now,
                )
            )
        
        draft.total_amount = sum(i.quantity * i.price_per_unit for i in draft.items)
        draft.updated_at = now
        return draft

    def remove_order_item(
        self, tenant_id: UUID, conversation_id: UUID, product_name: str
    ) -> OrderDraft | None:
        draft = self.get_order_draft(tenant_id, conversation_id)
        if not draft:
            return None
            
        draft.items = [i for i in draft.items if i.product_name != product_name]
        draft.total_amount = sum(i.quantity * i.price_per_unit for i in draft.items)
        draft.updated_at = datetime.now(UTC)
        return draft

    def confirm_order_draft(self, tenant_id: UUID, conversation_id: UUID) -> OrderDraft | None:
        draft = self.get_order_draft(tenant_id, conversation_id)
        if not draft:
            return None
        
        draft.status = "confirmed"
        draft.updated_at = datetime.now(UTC)
        return draft

    def update_order_draft_checkout_info(
        self, tenant_id: UUID, conversation_id: UUID, customer_phone: str, delivery_address: str
    ) -> OrderDraft | None:
        draft = self.get_order_draft(tenant_id, conversation_id)
        if not draft:
            return None
            
        draft.customer_phone = customer_phone
        draft.delivery_address = delivery_address
        draft.updated_at = datetime.now(UTC)
        return draft

    def revoke_api_key(self, tenant_id: UUID, key_id: UUID) -> bool:
        key = self.api_keys.get(key_id)
        if key and key.tenant_id == tenant_id and key.revoked_at is None:
            self.api_keys[key_id] = key.model_copy(update={"revoked_at": datetime.now(UTC)})
            return True
        return False

    def create_test_case(self, tenant_id: UUID, agent_id: UUID, payload: TestCaseCreate) -> TestCase:
        test_case = TestCase(
            tenant_id=tenant_id,
            agent_id=agent_id,
            name=payload.name,
            scenario=payload.scenario,
            expected_outcome=payload.expected_outcome,
        )
        self.test_cases[test_case.id] = test_case
        return test_case

    def list_test_cases(self, tenant_id: UUID, agent_id: UUID) -> list[TestCase]:
        return [tc for tc in self.test_cases.values() if tc.tenant_id == tenant_id and tc.agent_id == agent_id]

    def get_test_case(self, tenant_id: UUID, agent_id: UUID, test_case_id: UUID) -> TestCase | None:
        tc = self.test_cases.get(test_case_id)
        if tc and tc.tenant_id == tenant_id and tc.agent_id == agent_id:
            return tc
        return None

    def create_test_run(self, tenant_id: UUID, agent_id: UUID, test_case_id: UUID) -> TestRun:
        test_run = TestRun(
            tenant_id=tenant_id,
            agent_id=agent_id,
            test_case_id=test_case_id,
            status=TestCaseStatus.running,
            logs=[],
        )
        self.test_runs[test_run.id] = test_run
        return test_run

    def update_test_run(self, tenant_id: UUID, agent_id: UUID, test_run_id: UUID, status: TestCaseStatus, logs: list[dict[str, object]], result_summary: str | None = None) -> TestRun | None:
        tr = self.test_runs.get(test_run_id)
        if not tr or tr.tenant_id != tenant_id or tr.agent_id != agent_id:
            return None
        updated = tr.model_copy(update={"status": status, "logs": logs, "result_summary": result_summary, "updated_at": datetime.now(UTC)})
        self.test_runs[test_run_id] = updated
        return updated
        
    def list_test_runs(self, tenant_id: UUID, agent_id: UUID, test_case_id: UUID | None = None) -> list[TestRun]:
        res = [tr for tr in self.test_runs.values() if tr.tenant_id == tenant_id and tr.agent_id == agent_id]
        if test_case_id:
            res = [tr for tr in res if tr.test_case_id == test_case_id]
        return sorted(res, key=lambda x: x.created_at, reverse=True)


store = InMemoryStore()


def _is_refresh_session_usable(
    session: AuthSession | None,
    presented_refresh_token_hash: str,
    now: datetime,
) -> bool:
    if session is None or session.revoked_at is not None:
        return False
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > now and compare_digest(
        session.refresh_token_hash,
        presented_refresh_token_hash,
    )


def _normalize_suppression_contact_type(contact_type: str) -> str:
    normalized = contact_type.strip().lower()
    if normalized not in {"external_id", "phone"}:
        raise ValueError("contact_type must be external_id or phone")
    return normalized


def _normalize_suppression_channel(channel: str, contact_type: str) -> str:
    if contact_type == "phone":
        return "*"
    return channel.strip().lower()


def _normalize_suppression_value(contact_type: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("suppression value cannot be empty")
    if contact_type == "phone":
        digits = re.sub(r"\D+", "", normalized)
        
        # Russian phone normalization: 8 (9xx) -> +79xx
        if len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]
        elif len(digits) == 11 and digits.startswith("7"):
            pass
        elif len(digits) == 10 and digits.startswith("9"):
            digits = "7" + digits
            
        if len(digits) < 7:
            raise ValueError("phone suppression value must contain at least 7 digits")
        return f"+{digits}"
    return normalized.lower()


def _normalize_consent_type(consent_type: str) -> str:
    normalized = consent_type.strip().lower()
    if not normalized:
        raise ValueError("consent_type cannot be empty")
    return normalized


def _contact_lookup_candidates(
    channel: str,
    *,
    external_id: str | None = None,
    phone: str | None = None,
    contact_type: str | None = None,
    value: str | None = None,
) -> list[tuple[str, str, str]]:
    candidates: list[tuple[str, str, str]] = []
    if contact_type and value:
        normalized_type = _normalize_suppression_contact_type(contact_type)
        candidates.append(
            (
                _normalize_suppression_channel(channel, normalized_type),
                normalized_type,
                _normalize_suppression_value(normalized_type, value),
            )
        )
    if external_id:
        candidates.append(
            (
                _normalize_suppression_channel(channel, "external_id"),
                "external_id",
                _normalize_suppression_value("external_id", external_id),
            )
        )
        if _looks_like_phone(external_id):
            candidates.append(
                (
                    "*",
                    "phone",
                    _normalize_suppression_value("phone", external_id),
                )
            )
    if phone:
        try:
            normalized_phone = _normalize_suppression_value("phone", phone)
        except ValueError:
            normalized_phone = None
        if normalized_phone:
            candidates.append(("*", "phone", normalized_phone))
            candidates.append(
                (
                    _normalize_suppression_channel(channel, "phone"),
                    "phone",
                    normalized_phone,
                )
            )
    return candidates


def _is_contact_consent_active(consent: ContactConsent, now: datetime) -> bool:
    if consent.status != "active":
        return False
    if consent.expires_at is None:
        return True
    expires_at = consent.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at > now


def _looks_like_phone(value: str) -> bool:
    return len(re.sub(r"\D+", "", value)) >= 7
