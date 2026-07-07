import json
import re
from app.contracts.outbound import Campaign, CampaignLead
from collections.abc import Generator, Sequence
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta, timezone
from hmac import compare_digest
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from app.contracts.inbox import (
    ConversationTag,
    HandoffAssignment,
    InboxConversation,
    InternalNote,
)
from app.contracts.outbound import Campaign, CampaignLead
from app.contracts.voice import VoiceSession, VoiceSessionEvent
from app.db_models import (
    AgentModel,
    ApiKeyModel,
    AuditLogModel,
    AuthSessionModel,
    CampaignModel,
    CampaignLeadModel,
    ContactConsentModel,
    ContactSuppressionModel,
    ConversationModel,
    ConversationTagModel,
    CustomerModel,
    HandoffAssignmentModel,
    InternalNoteModel,
    KnowledgeChunkModel,
    KnowledgeIngestionJobModel,
    KnowledgeSourceModel,
    MembershipModel,
    MessageModel,
    OrderDraftModel,
    OrderItemModel,
    PasswordResetTokenModel,
    QAEvaluationModel,
    TenantModel,
    TestCaseModel,
    TestRunModel,
    UserModel,
    VerificationTokenModel,
    WeeklyReportModel,
)
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
    ContactConsent,
    ContactSuppression,
    Conversation,
    ConversationStatus,
    Customer,
    KnowledgeIngestionJob,
    KnowledgeIngestionJobStatus,
    KnowledgeSource,
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
    TenantStatus,
    TestCase,
    TestCaseCreate,
    TestCaseStatus,
    TestRun,
    User,
    VerificationToken,
    WeeklyReport,
    QAEvaluation,
)
from app.security import PasswordHash, hash_password, issue_access_token, verify_password
from app.settings import Settings


from app.store.base import BaseSqlAlchemyStore

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
                ("*", "phone", _normalize_suppression_value("phone", external_id))
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


def _is_contact_consent_model_active(model: ContactConsentModel, now: datetime) -> bool:
    if model.status != "active":
        return False
    if model.expires_at is None:
        return True
    expires_at = _timestamp(model.expires_at)
    return expires_at > now


def _looks_like_phone(value: str) -> bool:
    return len(re.sub(r"\D+", "", value)) >= 7


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


class AgentsStoreMixin(BaseSqlAlchemyStore):
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
                    pathway_nodes=agent.pathway_nodes,
                    pathway_edges=agent.pathway_edges,
                    business_profile=agent.business_profile,
                    agent_role=agent.agent_role,
                    agent_tone=agent.agent_tone,
                    agent_language=agent.agent_language,
                    business_hours=agent.business_hours,
                    escalation_rules=agent.escalation_rules,
                    sales_rules=agent.sales_rules,
                    forbidden_topics=agent.forbidden_topics,
                    enabled_tools=agent.enabled_tools,
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
            if (
                payload.telegram_bot_token is not None 
                and payload.telegram_bot_token != "***"
                and payload.telegram_bot_token != getattr(agent_model, "telegram_bot_token", None)
            ):
                agent_model.telegram_bot_token = payload.telegram_bot_token
                changed = True
            if (
                payload.pathway_nodes is not None
                and payload.pathway_nodes != getattr(agent_model, "pathway_nodes", None)
            ):
                agent_model.pathway_nodes = payload.pathway_nodes
                changed = True
            if (
                payload.pathway_edges is not None
                and payload.pathway_edges != getattr(agent_model, "pathway_edges", None)
            ):
                agent_model.pathway_edges = payload.pathway_edges
                changed = True
            if (
                payload.business_profile is not None
                and payload.business_profile != (agent_model.business_profile or "")
            ):
                agent_model.business_profile = payload.business_profile
                changed = True
                requires_republish = True
            if (
                payload.agent_role is not None
                and payload.agent_role != (agent_model.agent_role or "customer_support")
            ):
                agent_model.agent_role = payload.agent_role
                changed = True
                requires_republish = True
            if (
                payload.agent_tone is not None
                and payload.agent_tone != (agent_model.agent_tone or "professional")
            ):
                agent_model.agent_tone = payload.agent_tone
                changed = True
                requires_republish = True
            if (
                payload.agent_language is not None
                and payload.agent_language != (agent_model.agent_language or "ru")
            ):
                agent_model.agent_language = payload.agent_language
                changed = True
                requires_republish = True
            if (
                payload.business_hours is not None
                and payload.business_hours != (agent_model.business_hours or "")
            ):
                agent_model.business_hours = payload.business_hours
                changed = True
                requires_republish = True
            if (
                payload.escalation_rules is not None
                and payload.escalation_rules != (agent_model.escalation_rules or "")
            ):
                agent_model.escalation_rules = payload.escalation_rules
                changed = True
                requires_republish = True
            if (
                payload.sales_rules is not None
                and payload.sales_rules != (agent_model.sales_rules or "")
            ):
                agent_model.sales_rules = payload.sales_rules
                changed = True
                requires_republish = True
            if (
                payload.forbidden_topics is not None
                and payload.forbidden_topics != (agent_model.forbidden_topics or [])
            ):
                agent_model.forbidden_topics = payload.forbidden_topics
                changed = True
                requires_republish = True
            if (
                payload.enabled_tools is not None
                and payload.enabled_tools != (agent_model.enabled_tools or [])
            ):
                agent_model.enabled_tools = payload.enabled_tools
                changed = True
                requires_republish = True

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
                background_backend=self.background_jobs.backend_name,
                chunk_count=0,
            )
            session.add(job_model)
        self.background_jobs.submit('run_knowledge_ingestion', job_id, _store=self)
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
        try:
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
        except Exception as exc:
            with self._session_scope() as session:
                job_model = session.get(KnowledgeIngestionJobModel, str(job_id))
                if job_model:
                    job_model.status = KnowledgeIngestionJobStatus.failed
                    job_model.error_message = str(exc)
                    source_model = session.get(KnowledgeSourceModel, job_model.source_id)
                    if source_model:
                        source_model.status = KnowledgeSourceStatus.failed
            raise exc

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
            telegram_bot_token=getattr(model, "telegram_bot_token", None),
            pathway_nodes=getattr(model, "pathway_nodes", None),
            pathway_edges=getattr(model, "pathway_edges", None),
            business_profile=getattr(model, "business_profile", None) or "",
            agent_role=getattr(model, "agent_role", None) or "customer_support",
            agent_tone=getattr(model, "agent_tone", None) or "professional",
            agent_language=getattr(model, "agent_language", None) or "ru",
            business_hours=getattr(model, "business_hours", None) or "",
            escalation_rules=getattr(model, "escalation_rules", None) or "",
            sales_rules=getattr(model, "sales_rules", None) or "",
            forbidden_topics=getattr(model, "forbidden_topics", None) or [],
            enabled_tools=getattr(model, "enabled_tools", None) or ["escalate_to_human"],
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    def get_agent(self, tenant_id: UUID, agent_id: UUID) -> Agent | None:
        with self.session_factory() as session:
            agent_model = session.get(AgentModel, str(agent_id))
            if agent_model is None or agent_model.tenant_id != str(tenant_id):
                return None
            return self._agent_from_model(agent_model)

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
