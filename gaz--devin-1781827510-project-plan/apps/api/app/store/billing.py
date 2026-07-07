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


class BillingStoreMixin(BaseSqlAlchemyStore):
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

    @staticmethod
    def _tenant_from_model(model: TenantModel) -> Tenant:
        from app.encryption import decrypt_token
        from app.settings import get_settings
        
        settings = model.settings if isinstance(model.settings, dict) else {}
        
        # We don't want to mutate the model's settings dict, so we copy it
        parsed_settings = dict(settings)
        if "vk_group_token" in parsed_settings and parsed_settings["vk_group_token"]:
            secret = get_settings().access_token_secret
            decrypted = decrypt_token(str(parsed_settings["vk_group_token"]), secret)
            if decrypted:
                parsed_settings["vk_group_token"] = decrypted

        return Tenant(
            id=UUID(model.id),
            name=model.name,
            plan=model.plan,
            status=TenantStatus(model.status),
            settings=parsed_settings,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )
