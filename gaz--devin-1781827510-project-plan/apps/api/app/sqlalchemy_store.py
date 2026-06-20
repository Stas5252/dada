import json
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from hmac import compare_digest
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db_models import (
    AgentModel,
    ApiKeyModel,
    AuditLogModel,
    AuthSessionModel,
    ConversationModel,
    KnowledgeChunkModel,
    KnowledgeIngestionJobModel,
    KnowledgeSourceModel,
    MembershipModel,
    MessageModel,
    PasswordResetTokenModel,
    TenantModel,
    UserModel,
    VerificationTokenModel,
)
from app.demo_data import (
    DEMO_OWNER_PASSWORD,
    build_demo_agents,
    build_demo_chat_requests,
    build_demo_knowledge_sources,
    build_demo_owner,
    build_demo_tenant,
)
from app.rag import (
    build_knowledge_chunks,
    build_qdrant_collection_contract,
    compose_grounded_answer,
    ingestion_idempotency_key,
    retrieve_sources,
    upsert_chunks_to_qdrant,
)
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
    ChatMessageResponse,
    Conversation,
    ConversationStatus,
    KnowledgeIngestionJob,
    KnowledgeIngestionJobStatus,
    KnowledgeSource,
    KnowledgeSourceCreateRequest,
    KnowledgeSourceStatus,
    Message,
    MessageRole,
    PasswordResetToken,
    QdrantCollectionContract,
    RegisterRequest,
    Tenant,
    TenantStatus,
    User,
    VerificationToken,
)
from app.security import PasswordHash, hash_password, issue_access_token, verify_password
from app.settings import Settings


class SqlAlchemyStore:
    def __init__(self, session_factory: sessionmaker[Session], settings: Settings) -> None:
        self.session_factory = session_factory
        self.settings = settings

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
            role=Role.owner,
            email_verified=False,
        )
        with self._session_scope() as session:
            session.add(
                TenantModel(
                    id=str(tenant.id),
                    name=tenant.name,
                    plan=tenant.plan,
                    status=tenant.status,
                )
            )
            session.add(
                UserModel(
                    id=str(user.id),
                    tenant_id=str(tenant.id),
                    email=str(user.email),
                    password_hash=_dump_password_hash(hash_password(payload.password)),
                    name=user.name,
                    status="active",
                    email_verified=0,
                )
            )
            session.add(
                MembershipModel(
                    tenant_id=str(tenant.id),
                    user_id=str(user.id),
                    role=user.role,
                )
            )
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
        with self.session_factory() as session:
            user_model = session.scalar(select(UserModel).where(UserModel.email == email))
            if user_model is None:
                return None
            if not verify_password(password, _load_password_hash(user_model.password_hash)):
                return None
            tenant_model = session.get(TenantModel, user_model.tenant_id)
            if tenant_model is None:
                return None
            user = self._user_from_model(session, user_model)
            tenant = self._tenant_from_model(tenant_model)
        token = ""
        if not user.totp_secret:
            token = issue_access_token(
                tenant.id,
                user.id,
                token_secret,
                ttl_minutes=access_token_ttl_minutes,
            )
        return tenant, user, token

    def create_auth_session(
        self,
        session_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> AuthSession:
        with self._session_scope() as session:
            model = AuthSessionModel(
                id=str(session_id),
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                refresh_token_hash=refresh_token_hash,
                expires_at=expires_at,
            )
            session.add(model)
            session.flush()
            return self._auth_session_from_model(model)

    def rotate_auth_session(
        self,
        session_id: UUID,
        presented_refresh_token_hash: str,
        new_session_id: UUID,
        new_refresh_token_hash: str,
        new_expires_at: datetime,
    ) -> AuthSession | None:
        now = datetime.now(UTC)
        with self._session_scope() as session:
            current_model = session.get(AuthSessionModel, str(session_id))
            if not _is_refresh_session_model_usable(
                current_model,
                presented_refresh_token_hash,
                now,
            ):
                return None
            assert current_model is not None
            new_model = AuthSessionModel(
                id=str(new_session_id),
                tenant_id=current_model.tenant_id,
                user_id=current_model.user_id,
                refresh_token_hash=new_refresh_token_hash,
                expires_at=new_expires_at,
            )
            current_model.revoked_at = now
            current_model.replaced_by_session_id = str(new_session_id)
            current_model.updated_at = now
            session.add(new_model)
            session.flush()
            return self._auth_session_from_model(new_model)

    def revoke_auth_session(
        self,
        session_id: UUID,
        presented_refresh_token_hash: str,
    ) -> bool:
        now = datetime.now(UTC)
        with self._session_scope() as session:
            current_model = session.get(AuthSessionModel, str(session_id))
            if not _is_refresh_session_model_usable(
                current_model,
                presented_refresh_token_hash,
                now,
            ):
                return False
            assert current_model is not None
            current_model.revoked_at = now
            current_model.updated_at = now
            return True

    def get_tenant(self, tenant_id: UUID) -> Tenant | None:
        with self.session_factory() as session:
            tenant_model = session.get(TenantModel, str(tenant_id))
            return self._tenant_from_model(tenant_model) if tenant_model else None

    def update_tenant_settings(self, tenant_id: UUID, settings: dict[str, object]) -> Tenant | None:
        with self._session_scope() as session:
            tenant_model = session.get(TenantModel, str(tenant_id))
            if not tenant_model:
                return None
            tenant_model.settings = dict(settings)
            session.flush()
            return self._tenant_from_model(tenant_model)

    def get_user(self, user_id: UUID) -> User | None:
        with self.session_factory() as session:
            user_model = session.get(UserModel, str(user_id))
            return self._user_from_model(session, user_model) if user_model else None

    def get_user_by_email(self, email: str) -> User | None:
        with self.session_factory() as session:
            user_model = session.scalar(select(UserModel).where(UserModel.email == email))
            return self._user_from_model(session, user_model) if user_model else None

    def create_verification_token(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> VerificationToken:
        with self._session_scope() as session:
            model = VerificationTokenModel(
                id=str(uuid5(NAMESPACE_URL, token_hash)),
                user_id=str(user_id),
                token_hash=token_hash,
                expires_at=expires_at,
            )
            session.add(model)
            session.flush()
            return self._verification_token_from_model(model)

    def consume_verification_token(
        self, token_hash: str, now: datetime
    ) -> VerificationToken | None:
        with self._session_scope() as session:
            model = session.scalar(
                select(VerificationTokenModel).where(
                    VerificationTokenModel.token_hash == token_hash
                )
            )
            if not model or model.used_at or model.expires_at <= now:
                return None
            model.used_at = now
            session.flush()
            return self._verification_token_from_model(model)

    def verify_user_email(self, user_id: UUID) -> bool:
        with self._session_scope() as session:
            user_model = session.get(UserModel, str(user_id))
            if not user_model:
                return False
            user_model.email_verified = True
            return True

    def create_password_reset_token(
        self, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        with self._session_scope() as session:
            model = PasswordResetTokenModel(
                id=str(uuid5(NAMESPACE_URL, token_hash)),
                user_id=str(user_id),
                token_hash=token_hash,
                expires_at=expires_at,
            )
            session.add(model)
            session.flush()
            return self._password_reset_token_from_model(model)

    def consume_password_reset_token(
        self, token_hash: str, now: datetime
    ) -> PasswordResetToken | None:
        with self._session_scope() as session:
            model = session.scalar(
                select(PasswordResetTokenModel).where(
                    PasswordResetTokenModel.token_hash == token_hash
                )
            )
            if not model or model.used_at or model.expires_at <= now:
                return None
            model.used_at = now
            session.flush()
            return self._password_reset_token_from_model(model)

    def update_user_password(self, user_id: UUID, password_hash: PasswordHash) -> bool:
        with self._session_scope() as session:
            user_model = session.get(UserModel, str(user_id))
            if not user_model:
                return False
            user_model.password_hash = _dump_password_hash(password_hash)
            return True

    def update_user_mfa(
        self,
        user_id: UUID,
        totp_secret: str | None,
        recovery_code_hashes: list[str] | None = None,
    ) -> bool:
        with self._session_scope() as session:
            user_model = session.get(UserModel, str(user_id))
            if not user_model:
                return False
            user_model.totp_secret = totp_secret
            if recovery_code_hashes is not None:
                user_model.mfa_recovery_code_hashes = list(recovery_code_hashes)
            return True

    def replace_mfa_recovery_code_hashes(self, user_id: UUID, code_hashes: list[str]) -> bool:
        with self._session_scope() as session:
            user_model = session.get(UserModel, str(user_id))
            if not user_model or not user_model.totp_secret:
                return False
            user_model.mfa_recovery_code_hashes = list(code_hashes)
            return True

    def consume_mfa_recovery_code(self, user_id: UUID, code_hash: str) -> bool:
        with self._session_scope() as session:
            user_model = session.get(UserModel, str(user_id))
            if not user_model or not user_model.totp_secret:
                return False
            current_hashes = _load_recovery_code_hashes(user_model.mfa_recovery_code_hashes)
            remaining = [
                stored_hash
                for stored_hash in current_hashes
                if not compare_digest(stored_hash, code_hash)
            ]
            if len(remaining) == len(current_hashes):
                return False
            user_model.mfa_recovery_code_hashes = remaining
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
        with self._session_scope() as session:
            session.add(
                AuditLogModel(
                    id=str(audit_log.id),
                    tenant_id=str(audit_log.tenant_id) if audit_log.tenant_id else None,
                    user_id=str(audit_log.user_id) if audit_log.user_id else None,
                    event_type=audit_log.event_type,
                    ip_address=audit_log.ip_address,
                    details=audit_log.details,
                )
            )
        return audit_log

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
        )
        with self._session_scope() as session:
            session.add(
                AgentModel(
                    id=str(agent.id),
                    tenant_id=str(agent.tenant_id),
                    name=agent.name,
                    prompt=agent.prompt,
                    channel=agent.channel,
                    status=agent.status,
                    version=agent.version,
                    voice_id=agent.voice_id,
                    voice_language=agent.voice_language,
                    voice_speed=agent.voice_speed,
                    temperature=agent.temperature,
                    max_tokens=agent.max_tokens,
                    model_name=agent.model_name,
                )
            )
        return agent

    def list_agents(self, tenant_id: UUID) -> list[Agent]:
        with self.session_factory() as session:
            agent_models = session.scalars(
                select(AgentModel).where(AgentModel.tenant_id == str(tenant_id))
            ).all()
            return [self._agent_from_model(agent_model) for agent_model in agent_models]

    def update_agent(
        self,
        tenant_id: UUID,
        agent_id: UUID,
        payload: AgentUpdateRequest,
    ) -> Agent | None:
        with self._session_scope() as session:
            agent_model = session.get(AgentModel, str(agent_id))
            if agent_model is None or agent_model.tenant_id != str(tenant_id):
                return None

            changed = False
            requires_republish = False

            if payload.name is not None and payload.name != agent_model.name:
                agent_model.name = payload.name
                changed = True
            if payload.prompt is not None and payload.prompt != agent_model.prompt:
                agent_model.prompt = payload.prompt
                changed = True
                requires_republish = True
            if payload.channel is not None and payload.channel != agent_model.channel:
                agent_model.channel = payload.channel
                changed = True
                requires_republish = True
            if payload.voice_id is not None and payload.voice_id != agent_model.voice_id:
                agent_model.voice_id = payload.voice_id
                changed = True
            if (
                payload.voice_language is not None
                and payload.voice_language != agent_model.voice_language
            ):
                agent_model.voice_language = payload.voice_language
                changed = True
            if payload.voice_speed is not None and payload.voice_speed != agent_model.voice_speed:
                agent_model.voice_speed = payload.voice_speed
                changed = True
            if payload.temperature is not None and payload.temperature != agent_model.temperature:
                agent_model.temperature = payload.temperature
                changed = True
            if payload.max_tokens is not None and payload.max_tokens != agent_model.max_tokens:
                agent_model.max_tokens = payload.max_tokens
                changed = True
            if payload.model_name is not None and payload.model_name != agent_model.model_name:
                agent_model.model_name = payload.model_name
                changed = True

            if changed:
                agent_model.version += 1
                agent_model.updated_at = datetime.now(UTC)
                if requires_republish:
                    agent_model.status = AgentStatus.draft

            session.flush()
            return self._agent_from_model(agent_model)

    def publish_agent(self, tenant_id: UUID, agent_id: UUID) -> Agent | None:
        with self._session_scope() as session:
            agent_model = session.get(AgentModel, str(agent_id))
            if agent_model is None or agent_model.tenant_id != str(tenant_id):
                return None
            agent_model.status = AgentStatus.published
            agent_model.updated_at = datetime.now(UTC)
            session.flush()
            return self._agent_from_model(agent_model)

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
        with self._session_scope() as session:
            session.add(
                KnowledgeSourceModel(
                    id=str(source.id),
                    tenant_id=str(source.tenant_id),
                    title=source.title,
                    source_type=source.source_type,
                    content=source.content,
                    status=source.status,
                    chunk_count=source.chunk_count,
                )
            )
        self.enqueue_knowledge_ingestion(tenant_id, source.id)
        stored_source = self.get_knowledge_source(tenant_id, source.id)
        if stored_source is None:
            raise RuntimeError("knowledge source was not persisted")
        return stored_source

    def get_knowledge_source(self, tenant_id: UUID, source_id: UUID) -> KnowledgeSource | None:
        with self.session_factory() as session:
            source_model = session.get(KnowledgeSourceModel, str(source_id))
            if source_model is None or source_model.tenant_id != str(tenant_id):
                return None
            return self._knowledge_source_from_model(source_model)

    def list_knowledge_sources(self, tenant_id: UUID) -> list[KnowledgeSource]:
        with self.session_factory() as session:
            source_models = session.scalars(
                select(KnowledgeSourceModel).where(KnowledgeSourceModel.tenant_id == str(tenant_id))
            ).all()
            return [
                self._knowledge_source_from_model(source_model) for source_model in source_models
            ]

    def qdrant_collection_contract(self) -> QdrantCollectionContract:
        return build_qdrant_collection_contract(
            collection_name=self.settings.qdrant_collection_name,
            vector_size=self.settings.qdrant_vector_size,
            distance=self.settings.qdrant_distance,
        )

    def list_ingestion_jobs(self, tenant_id: UUID) -> list[KnowledgeIngestionJob]:
        with self.session_factory() as session:
            job_models = session.scalars(
                select(KnowledgeIngestionJobModel).where(
                    KnowledgeIngestionJobModel.tenant_id == str(tenant_id)
                )
            ).all()
            return [self._ingestion_job_from_model(job_model) for job_model in job_models]

    def enqueue_knowledge_ingestion(
        self,
        tenant_id: UUID,
        source_id: UUID,
    ) -> KnowledgeIngestionJob | None:
        source = self.get_knowledge_source(tenant_id, source_id)
        if source is None:
            return None
        idempotency_key = ingestion_idempotency_key(source)
        job_id = uuid5(NAMESPACE_URL, idempotency_key)
        with self._session_scope() as session:
            existing_job_model = session.scalar(
                select(KnowledgeIngestionJobModel).where(
                    KnowledgeIngestionJobModel.idempotency_key == idempotency_key
                )
            )
            if existing_job_model is not None:
                return self._ingestion_job_from_model(existing_job_model)
            contract = self.qdrant_collection_contract()
            job_model = KnowledgeIngestionJobModel(
                id=str(job_id),
                tenant_id=str(tenant_id),
                source_id=str(source.id),
                status=KnowledgeIngestionJobStatus.queued,
                idempotency_key=idempotency_key,
                qdrant_collection=contract.collection_name,
                background_backend="inline-sqlalchemy",
                chunk_count=0,
            )
            session.add(job_model)
        self.run_knowledge_ingestion(job_id)
        return self.get_ingestion_job(tenant_id, job_id)

    def get_ingestion_job(
        self,
        tenant_id: UUID,
        job_id: UUID,
    ) -> KnowledgeIngestionJob | None:
        with self.session_factory() as session:
            job_model = session.get(KnowledgeIngestionJobModel, str(job_id))
            if job_model is None or job_model.tenant_id != str(tenant_id):
                return None
            return self._ingestion_job_from_model(job_model)

    def run_knowledge_ingestion(self, job_id: UUID) -> None:
        with self._session_scope() as session:
            job_model = session.get(KnowledgeIngestionJobModel, str(job_id))
            if job_model is None:
                return
            job_model.status = KnowledgeIngestionJobStatus.running
            source_model = session.get(KnowledgeSourceModel, job_model.source_id)
            if source_model is None:
                job_model.status = KnowledgeIngestionJobStatus.failed
                job_model.error_message = "knowledge source not found"
                return
            source = self._knowledge_source_from_model(source_model)
            chunks = build_knowledge_chunks(source, self.settings.qdrant_vector_size)
            for chunk in chunks:
                session.merge(
                    KnowledgeChunkModel(
                        id=chunk.id,
                        tenant_id=str(chunk.tenant_id),
                        source_id=str(chunk.source_id),
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        content_hash=chunk.content_hash,
                        embedding=chunk.embedding,
                        qdrant_payload=chunk.qdrant_payload,
                    )
                )
            # Push the batch of chunks to Qdrant
            upsert_chunks_to_qdrant(chunks, job_model.qdrant_collection)
            source_model.status = KnowledgeSourceStatus.indexed
            source_model.chunk_count = len(chunks)
            job_model.status = KnowledgeIngestionJobStatus.completed
            job_model.chunk_count = len(chunks)

    def list_conversations(
        self,
        tenant_id: UUID,
        search: str | None = None,
        status: str | None = None,
        channel: str | None = None,
    ) -> list[Conversation]:
        with self.session_factory() as session:
            stmt = select(ConversationModel).where(ConversationModel.tenant_id == str(tenant_id))
            if status:
                stmt = stmt.where(ConversationModel.status == status)
            if channel:
                stmt = stmt.where(ConversationModel.channel == channel)
            if search:
                stmt = stmt.where(ConversationModel.summary.ilike(f"%{search}%"))
            conversation_models = session.scalars(stmt).all()
            return [self._conversation_from_model(model) for model in conversation_models]

    def count_messages(self, tenant_id: UUID) -> int:
        with self.session_factory() as session:
            return session.scalar(
                select(func.count(MessageModel.id)).where(MessageModel.tenant_id == str(tenant_id))
            ) or 0

    def add_chat_message(
        self,
        tenant_id: UUID,
        payload: ChatMessageRequest,
        agent_response_text: str | None = None,
    ) -> ChatMessageResponse:
        retrieval_results = retrieve_sources(
            tenant_id=tenant_id,
            query=payload.message,
            collection_name=self.settings.qdrant_collection_name,
            vector_size=self.settings.qdrant_vector_size,
            limit=1,
        )
        selected_result = retrieval_results[0] if retrieval_results else None

        sources = self.list_knowledge_sources(tenant_id)
        selected_source = (
            next((source for source in sources if source.id == selected_result.source_id), None)
            if selected_result
            else None
        )
        source_ids = [selected_source.id] if selected_source else []
        conversation = Conversation(
            tenant_id=tenant_id,
            agent_id=payload.agent_id,
            channel=payload.channel,
            status=ConversationStatus.resolved if selected_source else ConversationStatus.escalated,
            summary=payload.message[:160],
            resolution_status="resolved" if selected_source else "needs_operator",
        )
        customer_message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            role=MessageRole.customer,
            content=payload.message,
        )
        agent_message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            role=MessageRole.agent,
            content=agent_response_text
            if agent_response_text
            else compose_grounded_answer(payload.message, selected_result),
            confidence=0.86 if selected_source else 0.2,
            source_ids=source_ids,
        )
        with self._session_scope() as session:
            session.add(
                ConversationModel(
                    id=str(conversation.id),
                    tenant_id=str(conversation.tenant_id),
                    agent_id=str(conversation.agent_id),
                    channel=conversation.channel,
                    status=conversation.status,
                    summary=conversation.summary,
                    resolution_status=conversation.resolution_status,
                )
            )
            session.add(self._message_to_model(customer_message))
            session.add(self._message_to_model(agent_message))
        return ChatMessageResponse(
            conversation=conversation,
            customer_message=customer_message,
            agent_message=agent_message,
            sources=[selected_source] if selected_source else [],
        )

    def answer_chat(
        self,
        tenant_id: UUID,
        payload: ChatMessageRequest,
        agent_response_text: str | None = None,
    ) -> tuple[Conversation, Message, Message, list[KnowledgeSource]] | None:
        return self.record_chat_turn(
            tenant_id=tenant_id,
            agent_id=payload.agent_id,
            conversation_id=uuid4(),
            channel=payload.channel,
            customer_text=payload.message,
            agent_response_text=agent_response_text,
        )

    def record_chat_turn(
        self,
        tenant_id: UUID,
        agent_id: UUID,
        conversation_id: UUID,
        channel: str,
        customer_text: str,
        agent_response_text: str | None = None,
    ) -> tuple[Conversation, Message, Message, list[KnowledgeSource]] | None:
        agent = self.get_agent(tenant_id, agent_id)
        if agent is None:
            return None
        payload = ChatMessageRequest(agent_id=agent_id, channel=channel, message=customer_text)
        retrieval_results = retrieve_sources(
            tenant_id=tenant_id,
            query=payload.message,
            collection_name=self.settings.qdrant_collection_name,
            vector_size=self.settings.qdrant_vector_size,
            limit=1,
        )
        selected_result = retrieval_results[0] if retrieval_results else None

        sources = self.list_knowledge_sources(tenant_id)
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

        customer_message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.customer,
            content=payload.message,
        )
        agent_message = Message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=MessageRole.agent,
            content=agent_response_text
            if agent_response_text
            else compose_grounded_answer(payload.message, selected_result),
            confidence=0.86 if selected_source else 0.2,
            source_ids=source_ids,
        )

        with self._session_scope() as session:
            conversation_model = session.get(ConversationModel, str(conversation_id))
            if conversation_model is not None:
                if conversation_model.tenant_id != str(
                    tenant_id
                ) or conversation_model.agent_id != str(agent_id):
                    return None
                conversation_model.channel = channel
                conversation_model.status = status_value
                conversation_model.resolution_status = resolution_status
                if not conversation_model.summary:
                    conversation_model.summary = payload.message[:160]
            else:
                conversation_model = ConversationModel(
                    id=str(conversation_id),
                    tenant_id=str(tenant_id),
                    agent_id=str(agent_id),
                    channel=channel,
                    status=status_value,
                    summary=payload.message[:160],
                    resolution_status=resolution_status,
                )
                session.add(conversation_model)
            session.add(self._message_to_model(customer_message))
            session.add(self._message_to_model(agent_message))

            conversation = Conversation(
                id=conversation_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                channel=channel,
                status=status_value,
                summary=conversation_model.summary,
                resolution_status=resolution_status,
                created_at=_timestamp(conversation_model.created_at),
                updated_at=datetime.now(UTC),
            )
        return (
            conversation,
            customer_message,
            agent_message,
            [selected_source] if selected_source else [],
        )

    def get_conversation_detail(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
    ) -> tuple[Conversation, list[Message], list[KnowledgeSource]] | None:
        with self.session_factory() as session:
            conversation_model = session.get(ConversationModel, str(conversation_id))
            if conversation_model is None or conversation_model.tenant_id != str(tenant_id):
                return None
            message_models = session.scalars(
                select(MessageModel).where(MessageModel.conversation_id == str(conversation_id))
            ).all()
            messages = [self._message_from_model(message_model) for message_model in message_models]
            source_ids = {source_id for message in messages for source_id in message.source_ids}
            sources = [
                self._knowledge_source_from_model(source_model)
                for source_model in session.scalars(
                    select(KnowledgeSourceModel).where(
                        KnowledgeSourceModel.id.in_([str(source_id) for source_id in source_ids])
                    )
                ).all()
            ]
            return self._conversation_from_model(conversation_model), messages, sources

    def dashboard(self, tenant_id: UUID) -> tuple[Tenant, int, int, int, int, float] | None:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        agents_total = len(self.list_agents(tenant_id))
        sources_total = len(self.list_knowledge_sources(tenant_id))
        conversations = self.list_conversations(tenant_id)
        conversations_total = len(conversations)
        unresolved_total = len(
            [
                conversation
                for conversation in conversations
                if conversation.status != ConversationStatus.resolved
            ]
        )
        automation_rate = (
            (conversations_total - unresolved_total) / conversations_total
            if conversations_total
            else 0.0
        )
        return (
            tenant,
            agents_total,
            sources_total,
            conversations_total,
            unresolved_total,
            automation_rate,
        )

    def list_tenant_users(self, tenant_id: UUID) -> list[User]:
        with self.session_factory() as session:
            user_models = session.scalars(
                select(UserModel).where(UserModel.tenant_id == str(tenant_id))
            ).all()
            return [self._user_from_model(session, um) for um in user_models]

    def create_tenant_user(self, user: User, password: str) -> None:
        with self._session_scope() as session:
            session.add(
                UserModel(
                    id=str(user.id),
                    tenant_id=str(user.tenant_id),
                    email=user.email,
                    password_hash=_dump_password_hash(hash_password(password)),
                    name=user.name,
                    status="active",
                    email_verified=int(user.email_verified),
                )
            )
            session.add(
                MembershipModel(
                    tenant_id=str(user.tenant_id),
                    user_id=str(user.id),
                    role=user.role,
                )
            )

    def update_user_role(self, tenant_id: UUID, user_id: UUID, role: Role) -> User | None:
        with self._session_scope() as session:
            membership = session.scalar(
                select(MembershipModel).where(
                    MembershipModel.user_id == str(user_id),
                    MembershipModel.tenant_id == str(tenant_id),
                )
            )
            if membership:
                membership.role = role
            else:
                session.add(
                    MembershipModel(
                        tenant_id=str(tenant_id),
                        user_id=str(user_id),
                        role=role,
                    )
                )
            user_model = session.get(UserModel, str(user_id))
            if user_model:
                return self._user_from_model(session, user_model)
            return None

    def remove_tenant_user(self, tenant_id: UUID, user_id: UUID) -> None:
        with self._session_scope() as session:
            membership = session.scalar(
                select(MembershipModel).where(
                    MembershipModel.user_id == str(user_id),
                    MembershipModel.tenant_id == str(tenant_id),
                )
            )
            if membership:
                session.delete(membership)
            user_model = session.get(UserModel, str(user_id))
            if user_model and user_model.tenant_id == str(tenant_id):
                session.delete(user_model)

    def create_api_key(
        self,
        tenant_id: UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        created_by: UUID,
        scopes: list[str],
    ) -> ApiKey:
        with self._session_scope() as session:
            model = ApiKeyModel(
                id=str(uuid5(NAMESPACE_URL, key_hash)),
                tenant_id=str(tenant_id),
                name=name,
                key_prefix=key_prefix,
                key_hash=key_hash,
                created_by=str(created_by),
                scopes=scopes,
            )
            session.add(model)
            session.flush()
            return ApiKey(
                id=UUID(model.id),
                tenant_id=UUID(model.tenant_id),
                name=model.name,
                key_prefix=model.key_prefix,
                key_hash=model.key_hash,
                created_by=UUID(model.created_by),
                scopes=model.scopes,
                created_at=_timestamp(model.created_at),
                last_used_at=_timestamp(model.last_used_at) if model.last_used_at else None,
                revoked_at=_timestamp(model.revoked_at) if model.revoked_at else None,
            )

    def list_api_keys(self, tenant_id: UUID) -> list[ApiKey]:
        with self.session_factory() as session:
            models = session.scalars(
                select(ApiKeyModel).where(ApiKeyModel.tenant_id == str(tenant_id))
            ).all()
            return [
                ApiKey(
                    id=UUID(m.id),
                    tenant_id=UUID(m.tenant_id),
                    name=m.name,
                    key_prefix=m.key_prefix,
                    key_hash=m.key_hash,
                    created_by=UUID(m.created_by),
                    scopes=m.scopes,
                    created_at=_timestamp(m.created_at),
                    last_used_at=_timestamp(m.last_used_at) if m.last_used_at else None,
                    revoked_at=_timestamp(m.revoked_at) if m.revoked_at else None,
                )
                for m in models
            ]

    def revoke_api_key(self, tenant_id: UUID, key_id: UUID) -> bool:
        with self._session_scope() as session:
            model = session.get(ApiKeyModel, str(key_id))
            if model and model.tenant_id == str(tenant_id) and model.revoked_at is None:
                model.revoked_at = datetime.now(UTC)
                return True
            return False

    def seed_demo_data(
        self,
        tenant_id: UUID,
        token_secret: str,
    ) -> Tenant:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            tenant = build_demo_tenant(tenant_id)
            owner = build_demo_owner(tenant.id)
            with self._session_scope() as session:
                session.add(
                    TenantModel(
                        id=str(tenant.id),
                        name=tenant.name,
                        plan=tenant.plan,
                        status=tenant.status,
                    )
                )
                session.add(
                    UserModel(
                        id=str(owner.id),
                        tenant_id=str(tenant.id),
                        email=str(owner.email),
                        password_hash=_dump_password_hash(hash_password(DEMO_OWNER_PASSWORD)),
                        name=owner.name,
                        status="active",
                    )
                )
                session.add(
                    MembershipModel(
                        tenant_id=str(tenant.id),
                        user_id=str(owner.id),
                        role=owner.role,
                    )
                )

        if not self.list_agents(tenant_id):
            with self._session_scope() as session:
                for agent in build_demo_agents(tenant_id):
                    session.add(
                        AgentModel(
                            id=str(agent.id),
                            tenant_id=str(agent.tenant_id),
                            name=agent.name,
                            prompt=agent.prompt,
                            channel=agent.channel,
                            status=agent.status,
                            version=agent.version,
                        )
                    )

        if not self.list_knowledge_sources(tenant_id):
            with self._session_scope() as session:
                for source in build_demo_knowledge_sources(tenant_id):
                    session.add(
                        KnowledgeSourceModel(
                            id=str(source.id),
                            tenant_id=str(source.tenant_id),
                            title=source.title,
                            source_type=source.source_type,
                            content=source.content,
                            status=source.status,
                            chunk_count=source.chunk_count,
                        )
                    )
            for source in build_demo_knowledge_sources(tenant_id):
                self.enqueue_knowledge_ingestion(tenant_id, source.id)

        if not self.list_conversations(tenant_id):
            primary_agent = build_demo_agents(tenant_id)[0]
            for chat_request in build_demo_chat_requests(primary_agent.id):
                self.answer_chat(tenant_id, chat_request)

        issue_access_token(tenant_id, build_demo_owner(tenant_id).id, token_secret)
        seeded_tenant = self.get_tenant(tenant_id)
        if seeded_tenant is None:
            raise RuntimeError("demo tenant was not persisted")
        return seeded_tenant

    def _session_scope(self) -> AbstractContextManager[Session]:
        return _SessionScope(self.session_factory)

    @staticmethod
    def _tenant_from_model(model: TenantModel) -> Tenant:
        return Tenant(
            id=UUID(model.id),
            name=model.name,
            plan=model.plan,
            status=TenantStatus(model.status),
            settings=model.settings if isinstance(model.settings, dict) else {},
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    @staticmethod
    def _user_from_model(session: Session, model: UserModel) -> User:
        membership = session.scalar(
            select(MembershipModel).where(MembershipModel.user_id == model.id)
        )
        role = Role(membership.role) if membership else Role.owner
        return User(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            email=model.email,
            name=model.name,
            role=role,
            email_verified=bool(model.email_verified),
            totp_secret=model.totp_secret,
            mfa_recovery_code_hashes=_load_recovery_code_hashes(model.mfa_recovery_code_hashes),
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.created_at),
        )

    @staticmethod
    def _verification_token_from_model(model: VerificationTokenModel) -> VerificationToken:
        return VerificationToken(
            id=UUID(model.id),
            user_id=UUID(model.user_id),
            token_hash=model.token_hash,
            expires_at=_timestamp(model.expires_at),
            used_at=_timestamp(model.used_at) if model.used_at else None,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.created_at),
        )

    @staticmethod
    def _password_reset_token_from_model(model: PasswordResetTokenModel) -> PasswordResetToken:
        return PasswordResetToken(
            id=UUID(model.id),
            user_id=UUID(model.user_id),
            token_hash=model.token_hash,
            expires_at=_timestamp(model.expires_at),
            used_at=_timestamp(model.used_at) if model.used_at else None,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.created_at),
        )

    @staticmethod
    def _auth_session_from_model(model: AuthSessionModel) -> AuthSession:
        return AuthSession(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            user_id=UUID(model.user_id),
            refresh_token_hash=model.refresh_token_hash,
            expires_at=_timestamp(model.expires_at),
            revoked_at=_timestamp(model.revoked_at) if model.revoked_at else None,
            replaced_by_session_id=(
                UUID(model.replaced_by_session_id) if model.replaced_by_session_id else None
            ),
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    @staticmethod
    def _agent_from_model(model: AgentModel) -> Agent:
        return Agent(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            name=model.name,
            prompt=model.prompt,
            status=AgentStatus(model.status),
            channel=model.channel,
            version=model.version,
            voice_id=model.voice_id,
            voice_language=model.voice_language,
            voice_speed=model.voice_speed,
            temperature=model.temperature,
            max_tokens=model.max_tokens,
            model_name=model.model_name,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    def get_agent(self, tenant_id: UUID, agent_id: UUID) -> Agent | None:
        with self.session_factory() as session:
            agent_model = session.get(AgentModel, str(agent_id))
            if agent_model is None or agent_model.tenant_id != str(tenant_id):
                return None
            return self._agent_from_model(agent_model)

    def get_conversation(self, tenant_id: UUID, conversation_id: UUID) -> Conversation | None:
        with self.session_factory() as session:
            conversation_model = session.get(ConversationModel, str(conversation_id))
            if conversation_model is None or conversation_model.tenant_id != str(tenant_id):
                return None
            return self._conversation_from_model(conversation_model)

    @staticmethod
    def _knowledge_source_from_model(model: KnowledgeSourceModel) -> KnowledgeSource:
        return KnowledgeSource(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            title=model.title,
            source_type=model.source_type,
            content=model.content,
            status=KnowledgeSourceStatus(model.status),
            chunk_count=model.chunk_count,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.created_at),
        )

    @staticmethod
    def _ingestion_job_from_model(model: KnowledgeIngestionJobModel) -> KnowledgeIngestionJob:
        return KnowledgeIngestionJob(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            source_id=UUID(model.source_id),
            status=KnowledgeIngestionJobStatus(model.status),
            idempotency_key=model.idempotency_key,
            qdrant_collection=model.qdrant_collection,
            background_backend=model.background_backend,
            chunk_count=model.chunk_count,
            error_message=model.error_message,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    @staticmethod
    def _conversation_from_model(model: ConversationModel) -> Conversation:
        return Conversation(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            agent_id=UUID(model.agent_id),
            channel=model.channel,
            status=ConversationStatus(model.status),
            summary=model.summary,
            resolution_status=model.resolution_status,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.created_at),
        )

    @staticmethod
    def _message_to_model(message: Message) -> MessageModel:
        return MessageModel(
            id=str(message.id),
            tenant_id=str(message.tenant_id),
            conversation_id=str(message.conversation_id),
            role=message.role,
            content=message.content,
            confidence=message.confidence,
            source_ids=[str(source_id) for source_id in message.source_ids],
        )

    @staticmethod
    def _message_from_model(model: MessageModel) -> Message:
        return Message(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            conversation_id=UUID(model.conversation_id),
            role=MessageRole(model.role),
            content=model.content,
            confidence=model.confidence,
            source_ids=[UUID(source_id) for source_id in model.source_ids],
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.created_at),
        )


class _SessionScope:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> Session:
        self.session = self.session_factory()
        return self.session

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object,
    ) -> None:
        if self.session is None:
            return
        if exc_type is None:
            self.session.commit()
        else:
            self.session.rollback()
        self.session.close()


def _dump_password_hash(password_hash: PasswordHash) -> str:
    return json.dumps(
        {
            "algorithm": password_hash.algorithm,
            "iterations": password_hash.iterations,
            "salt": password_hash.salt,
            "digest": password_hash.digest,
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _load_password_hash(value: str) -> PasswordHash:
    payload = json.loads(value)
    return PasswordHash(
        algorithm=str(payload["algorithm"]),
        iterations=int(payload["iterations"]),
        salt=str(payload["salt"]),
        digest=str(payload["digest"]),
    )


def _load_recovery_code_hashes(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(payload, list):
            return [str(item) for item in payload]
    return []


def _timestamp(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _is_refresh_session_model_usable(
    model: AuthSessionModel | None,
    presented_refresh_token_hash: str,
    now: datetime,
) -> bool:
    if model is None or model.revoked_at is not None:
        return False
    expires_at = _timestamp(model.expires_at)
    return expires_at > now and compare_digest(
        model.refresh_token_hash,
        presented_refresh_token_hash,
    )
