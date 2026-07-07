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


class AuthStoreMixin(BaseSqlAlchemyStore):
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
            if current_model is None:
                return False
            current_model.revoked_at = now
            current_model.updated_at = now
            return True

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
