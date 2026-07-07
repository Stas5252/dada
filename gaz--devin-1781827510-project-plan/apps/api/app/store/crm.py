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


class CrmStoreMixin(BaseSqlAlchemyStore):
    def get_customer(self, tenant_id: UUID, customer_id: UUID) -> Customer | None:
        with self._session_scope() as session:
            customer_model = session.get(CustomerModel, str(customer_id))
            if customer_model is None or customer_model.tenant_id != str(tenant_id):
                return None
            return self._customer_from_model(customer_model)

    def get_customer_by_external_id(
        self, tenant_id: UUID, channel: str, external_id: str
    ) -> Customer | None:
        with self._session_scope() as session:
            model = session.scalar(
                select(CustomerModel).where(
                    CustomerModel.tenant_id == str(tenant_id),
                    CustomerModel.channel == channel,
                    CustomerModel.external_id == external_id,
                )
            )
            return self._customer_from_model(model) if model else None

    def create_customer(
        self,
        tenant_id: UUID,
        channel: str,
        external_id: str,
        name: str | None = None,
        phone: str | None = None,
    ) -> Customer:
        with self._session_scope() as session:
            model = CustomerModel(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                external_id=external_id,
                channel=channel,
                name=name,
                phone=phone,
                tags=[],
            )
            session.add(model)
            session.flush()
            return self._customer_from_model(model)

    def update_customer(
        self,
        tenant_id: UUID,
        customer_id: UUID,
        name: str | None = None,
        phone: str | None = None,
        tags: list[str] | None = None,
    ) -> Customer | None:
        with self._session_scope() as session:
            model = session.get(CustomerModel, str(customer_id))
            if model is None or model.tenant_id != str(tenant_id):
                return None
            if name is not None:
                model.name = name
            if phone is not None:
                model.phone = phone
            if tags is not None:
                model.tags = list(tags)
            model.updated_at = datetime.now(UTC)
            session.flush()
            return self._customer_from_model(model)

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
        now = datetime.now(UTC)

        with self._session_scope() as session:
            model = session.scalar(
                select(ContactSuppressionModel).where(
                    ContactSuppressionModel.tenant_id == str(tenant_id),
                    ContactSuppressionModel.channel == normalized_channel,
                    ContactSuppressionModel.contact_type == normalized_type,
                    ContactSuppressionModel.value == normalized_value,
                )
            )
            if model is None:
                model = ContactSuppressionModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    channel=normalized_channel,
                    contact_type=normalized_type,
                    value=normalized_value,
                    reason=reason,
                    source=source,
                    status="active",
                )
                session.add(model)
            else:
                model.reason = reason
                model.source = source
                model.status = "active"
                model.updated_at = now

            session.add(
                AuditLogModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    user_id=None,
                    event_type="contact_suppression.recorded",
                    ip_address=None,
                    details={
                        "channel": normalized_channel,
                        "contact_type": normalized_type,
                        "reason": reason,
                        "source": source,
                        "status": "active",
                        "value": normalized_value,
                    },
                )
            )
            session.flush()
            return self._contact_suppression_from_model(model)

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
                candidates.append(("*", "phone", _normalize_suppression_value("phone", external_id)))
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

        if not candidates:
            return None

        with self._session_scope() as session:
            for candidate_channel, candidate_type, candidate_value in candidates:
                stmt = select(ContactSuppressionModel).where(
                    ContactSuppressionModel.tenant_id == str(tenant_id),
                    ContactSuppressionModel.channel == candidate_channel,
                    ContactSuppressionModel.contact_type == candidate_type,
                    ContactSuppressionModel.value == candidate_value,
                )
                if not include_revoked:
                    stmt = stmt.where(ContactSuppressionModel.status == "active")
                model = session.scalar(stmt)
                if model:
                    return self._contact_suppression_from_model(model)
        return None

    def list_contact_suppressions(self, tenant_id: UUID) -> list[ContactSuppression]:
        with self._session_scope() as session:
            models = session.scalars(
                select(ContactSuppressionModel)
                .where(ContactSuppressionModel.tenant_id == str(tenant_id))
                .order_by(ContactSuppressionModel.updated_at.desc())
            ).all()
            return [self._contact_suppression_from_model(model) for model in models]

    def revoke_contact_suppression(
        self,
        tenant_id: UUID,
        suppression_id: UUID,
    ) -> ContactSuppression | None:
        with self._session_scope() as session:
            model = session.get(ContactSuppressionModel, str(suppression_id))
            if model is None or model.tenant_id != str(tenant_id):
                return None
            model.status = "revoked"
            model.updated_at = datetime.now(UTC)
            session.add(
                AuditLogModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    user_id=None,
                    event_type="contact_suppression.revoked",
                    ip_address=None,
                    details={
                        "channel": model.channel,
                        "contact_type": model.contact_type,
                        "status": model.status,
                        "value": model.value,
                    },
                )
            )
            session.flush()
            return self._contact_suppression_from_model(model)

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
        now = datetime.now(UTC)

        with self._session_scope() as session:
            model = session.scalar(
                select(ContactConsentModel).where(
                    ContactConsentModel.tenant_id == str(tenant_id),
                    ContactConsentModel.channel == normalized_channel,
                    ContactConsentModel.contact_type == normalized_type,
                    ContactConsentModel.value == normalized_value,
                    ContactConsentModel.consent_type == normalized_consent_type,
                )
            )
            if model is None:
                model = ContactConsentModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    channel=normalized_channel,
                    contact_type=normalized_type,
                    value=normalized_value,
                    consent_type=normalized_consent_type,
                    source=source,
                    status="active",
                    expires_at=expires_at,
                )
                session.add(model)
            else:
                model.source = source
                model.status = "active"
                model.expires_at = expires_at
                model.updated_at = now

            session.add(
                AuditLogModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    user_id=None,
                    event_type="contact_consent.recorded",
                    ip_address=None,
                    details={
                        "channel": normalized_channel,
                        "consent_type": normalized_consent_type,
                        "contact_type": normalized_type,
                        "source": source,
                        "status": "active",
                        "value": normalized_value,
                    },
                )
            )
            session.flush()
            return self._contact_consent_from_model(model)

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
        if not candidates:
            return None

        normalized_consent_type = _normalize_consent_type(consent_type)
        now = datetime.now(UTC)
        with self._session_scope() as session:
            for candidate_channel, candidate_type, candidate_value in candidates:
                stmt = select(ContactConsentModel).where(
                    ContactConsentModel.tenant_id == str(tenant_id),
                    ContactConsentModel.channel == candidate_channel,
                    ContactConsentModel.contact_type == candidate_type,
                    ContactConsentModel.value == candidate_value,
                    ContactConsentModel.consent_type == normalized_consent_type,
                )
                if not include_revoked:
                    stmt = stmt.where(ContactConsentModel.status == "active")
                model = session.scalar(stmt)
                if model and (
                    include_revoked or _is_contact_consent_model_active(model, now)
                ):
                    return self._contact_consent_from_model(model)
        return None

    def list_contact_consents(self, tenant_id: UUID) -> list[ContactConsent]:
        with self._session_scope() as session:
            models = session.scalars(
                select(ContactConsentModel)
                .where(ContactConsentModel.tenant_id == str(tenant_id))
                .order_by(ContactConsentModel.updated_at.desc())
            ).all()
            return [self._contact_consent_from_model(model) for model in models]

    def revoke_contact_consent(
        self,
        tenant_id: UUID,
        consent_id: UUID,
    ) -> ContactConsent | None:
        with self._session_scope() as session:
            model = session.get(ContactConsentModel, str(consent_id))
            if model is None or model.tenant_id != str(tenant_id):
                return None
            model.status = "revoked"
            model.updated_at = datetime.now(UTC)
            session.add(
                AuditLogModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    user_id=None,
                    event_type="contact_consent.revoked",
                    ip_address=None,
                    details={
                        "channel": model.channel,
                        "consent_type": model.consent_type,
                        "contact_type": model.contact_type,
                        "status": model.status,
                        "value": model.value,
                    },
                )
            )
            session.flush()
            return self._contact_consent_from_model(model)

    def create_campaign(self, tenant_id: UUID, name: str, agent_id: str, max_attempts: int, retry_delay_minutes: int) -> Campaign:
        with self._session_scope() as session:
            campaign_id = str(uuid4())
            db_campaign = CampaignModel(
                id=campaign_id,
                tenant_id=str(tenant_id),
                agent_id=agent_id,
                name=name,
                status="draft",
                max_attempts=max_attempts,
                retry_delay_minutes=retry_delay_minutes
            )
            session.add(db_campaign)
            session.commit()
            return Campaign.model_validate(db_campaign)

    def get_campaign(self, tenant_id: UUID, campaign_id: str) -> Campaign | None:
        with self._session_scope() as session:
            db_campaign = session.get(CampaignModel, campaign_id)
            if not db_campaign or db_campaign.tenant_id != str(tenant_id):
                return None
            return Campaign.model_validate(db_campaign)

    def list_campaigns(self, tenant_id: UUID) -> list[Campaign]:
        with self._session_scope() as session:
            stmt = select(CampaignModel).where(CampaignModel.tenant_id == str(tenant_id))
            result = session.execute(stmt)
            return [Campaign.model_validate(row) for row in result.scalars().all()]

    def update_campaign_status(self, tenant_id: UUID, campaign_id: str, status: str) -> Campaign | None:
        with self._session_scope() as session:
            db_campaign = session.get(CampaignModel, campaign_id)
            if not db_campaign or db_campaign.tenant_id != str(tenant_id):
                return None
            db_campaign.status = status
            session.commit()
            return Campaign.model_validate(db_campaign)

    def add_campaign_lead(self, tenant_id: UUID, campaign_id: str, phone: str, variables: dict[str, Any]) -> CampaignLead:
        with self._session_scope() as session:
            lead_id = str(uuid4())
            db_lead = CampaignLeadModel(
                id=lead_id,
                tenant_id=str(tenant_id),
                campaign_id=campaign_id,
                phone=phone,
                variables=variables,
                status="pending",
                attempts=0
            )
            session.add(db_lead)
            session.commit()
            return CampaignLead.model_validate(db_lead)

    def list_campaign_leads(self, tenant_id: UUID, campaign_id: str) -> list[CampaignLead]:
        with self._session_scope() as session:
            stmt = select(CampaignLeadModel).where(
                CampaignLeadModel.tenant_id == str(tenant_id),
                CampaignLeadModel.campaign_id == campaign_id
            )
            result = session.execute(stmt)
            return [CampaignLead.model_validate(row) for row in result.scalars().all()]

    def update_campaign_lead(self, tenant_id: UUID, lead_id: str, status: str | None = None, outcome: str | None = None, increment_attempt: bool = False) -> CampaignLead | None:
        with self._session_scope() as session:
            db_lead = session.get(CampaignLeadModel, lead_id)
            if not db_lead or db_lead.tenant_id != str(tenant_id):
                return None
            if status is not None:
                db_lead.status = status
            if outcome is not None:
                db_lead.outcome = outcome
            if increment_attempt:
                db_lead.attempts += 1
                db_lead.last_attempt_at = func.now()
            session.commit()
            return CampaignLead.model_validate(db_lead)

    def get_due_campaign_leads(self) -> list[CampaignLead]:
        # Simple implementation: get all leads that are in 'pending' status for 'active' campaigns
        # or 'failed' status but under max_attempts and retry_delay has passed
        with self._session_scope() as session:
            # Active campaigns
            active_campaigns_stmt = select(CampaignModel).where(CampaignModel.status == "active")
            active_campaigns = session.execute(active_campaigns_stmt).scalars().all()
            if not active_campaigns:
                return []
            
            campaign_map = {c.id: c for c in active_campaigns}
            active_campaign_ids = list(campaign_map.keys())
            
            stmt = select(CampaignLeadModel).where(
                CampaignLeadModel.campaign_id.in_(active_campaign_ids),
                CampaignLeadModel.status.in_(["pending", "failed"])
            )
            leads = session.execute(stmt).scalars().all()
            
            due_leads = []
            for lead in leads:
                campaign = campaign_map[lead.campaign_id]
                if lead.status == "pending":
                    due_leads.append(CampaignLead.model_validate(lead))
                elif lead.status == "failed" and lead.attempts < campaign.max_attempts:
                    if lead.last_attempt_at:
                        from datetime import datetime, timezone, timedelta
                        now = datetime.now(timezone.utc)
                        delta = now - lead.last_attempt_at
                        if delta.total_seconds() / 60.0 >= campaign.retry_delay_minutes:
                            due_leads.append(CampaignLead.model_validate(lead))
                    else:
                        due_leads.append(CampaignLead.model_validate(lead))

            return due_leads

    def get_order_draft(self, tenant_id: UUID, conversation_id: UUID) -> OrderDraft | None:
        with self._session_scope() as session:
            draft_model = session.scalar(
                select(OrderDraftModel).where(
                    OrderDraftModel.tenant_id == str(tenant_id),
                    OrderDraftModel.conversation_id == str(conversation_id)
                )
            )
            if not draft_model:
                return None
            items_models = session.scalars(
                select(OrderItemModel).where(OrderItemModel.order_id == draft_model.id)
            ).all()
            return self._order_draft_from_model(draft_model, items_models)

    def add_order_item(
        self, tenant_id: UUID, conversation_id: UUID, product_name: str, quantity: int, price_per_unit: int, product_external_id: str | None = None
    ) -> OrderDraft:
        with self._session_scope() as session:
            draft_model = session.scalar(
                select(OrderDraftModel).where(
                    OrderDraftModel.tenant_id == str(tenant_id),
                    OrderDraftModel.conversation_id == str(conversation_id)
                )
            )
            if not draft_model:
                draft_model = OrderDraftModel(
                    id=str(uuid4()),
                    tenant_id=str(tenant_id),
                    conversation_id=str(conversation_id),
                    status="draft",
                    total_amount=0,
                )
                session.add(draft_model)
                session.flush()

            existing_item = session.scalar(
                select(OrderItemModel).where(
                    OrderItemModel.order_id == draft_model.id,
                    OrderItemModel.product_name == product_name
                )
            )
            if existing_item:
                existing_item.quantity += quantity
            else:
                new_item = OrderItemModel(
                    id=str(uuid4()),
                    order_id=draft_model.id,
                    product_name=product_name,
                    product_external_id=product_external_id,
                    quantity=quantity,
                    price_per_unit=price_per_unit,
                )
                session.add(new_item)
            
            session.flush()
            
            # Recalculate total
            all_items = session.scalars(
                select(OrderItemModel).where(OrderItemModel.order_id == draft_model.id)
            ).all()
            draft_model.total_amount = sum(i.quantity * i.price_per_unit for i in all_items)
            session.flush()
            
            return self._order_draft_from_model(draft_model, all_items)

    def remove_order_item(
        self, tenant_id: UUID, conversation_id: UUID, product_name: str
    ) -> OrderDraft | None:
        with self._session_scope() as session:
            draft_model = session.scalar(
                select(OrderDraftModel).where(
                    OrderDraftModel.tenant_id == str(tenant_id),
                    OrderDraftModel.conversation_id == str(conversation_id)
                )
            )
            if not draft_model:
                return None

            item_model = session.scalar(
                select(OrderItemModel).where(
                    OrderItemModel.order_id == draft_model.id,
                    OrderItemModel.product_name == product_name
                )
            )
            if item_model:
                session.delete(item_model)
                session.flush()
            
            # Recalculate total
            all_items = session.scalars(
                select(OrderItemModel).where(OrderItemModel.order_id == draft_model.id)
            ).all()
            draft_model.total_amount = sum(i.quantity * i.price_per_unit for i in all_items)
            session.flush()

            return self._order_draft_from_model(draft_model, all_items)

    def confirm_order_draft(self, tenant_id: UUID, conversation_id: UUID) -> OrderDraft | None:
        with self._session_scope() as session:
            draft_model = session.scalar(
                select(OrderDraftModel).where(
                    OrderDraftModel.tenant_id == str(tenant_id),
                    OrderDraftModel.conversation_id == str(conversation_id)
                )
            )
            if not draft_model:
                return None

            draft_model.status = "confirmed"
            session.flush()
            
            all_items = session.scalars(
                select(OrderItemModel).where(OrderItemModel.order_id == draft_model.id)
            ).all()
            return self._order_draft_from_model(draft_model, all_items)

    def update_order_draft_checkout_info(
        self, tenant_id: UUID, conversation_id: UUID, customer_phone: str, delivery_address: str
    ) -> OrderDraft | None:
        with self._session_scope() as session:
            draft_model = session.scalar(
                select(OrderDraftModel).where(
                    OrderDraftModel.tenant_id == str(tenant_id),
                    OrderDraftModel.conversation_id == str(conversation_id)
                )
            )
            if not draft_model:
                return None
                
            draft_model.customer_phone = customer_phone
            draft_model.delivery_address = delivery_address
            session.flush()
            
            all_items = session.scalars(
                select(OrderItemModel).where(OrderItemModel.order_id == draft_model.id)
            ).all()
            return self._order_draft_from_model(draft_model, all_items)

    @staticmethod
    def _customer_from_model(model: CustomerModel) -> Customer:
        return Customer(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            external_id=model.external_id,
            channel=model.channel,
            name=model.name,
            phone=model.phone,
            tags=list(model.tags),
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    @staticmethod
    def _contact_suppression_from_model(model: ContactSuppressionModel) -> ContactSuppression:
        return ContactSuppression(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            channel=model.channel,
            contact_type=model.contact_type,
            value=model.value,
            reason=model.reason,
            source=model.source,
            status=model.status,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    @staticmethod
    def _contact_consent_from_model(model: ContactConsentModel) -> ContactConsent:
        return ContactConsent(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            channel=model.channel,
            contact_type=model.contact_type,
            value=model.value,
            consent_type=model.consent_type,
            source=model.source,
            status=model.status,
            expires_at=_timestamp(model.expires_at) if model.expires_at else None,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    @staticmethod
    def _order_item_from_model(item_model: OrderItemModel) -> OrderItem:
        return OrderItem(
            id=UUID(item_model.id),
            order_id=UUID(item_model.order_id),
            product_name=item_model.product_name,
            product_external_id=item_model.product_external_id,
            quantity=item_model.quantity,
            price_per_unit=item_model.price_per_unit,
            created_at=item_model.created_at,
        )

    @staticmethod
    def _order_draft_from_model(model: OrderDraftModel, items: Sequence[OrderItemModel]) -> OrderDraft:
        return OrderDraft(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            conversation_id=UUID(model.conversation_id),
            customer_phone=model.customer_phone,
            delivery_address=model.delivery_address,
            status=model.status,
            total_amount=model.total_amount,
            created_at=model.created_at,
            updated_at=model.updated_at,
            items=[CrmStoreMixin._order_item_from_model(i) for i in items],
        )
