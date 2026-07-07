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
    BillingLedgerEntryModel,
    CampaignModel,
    CampaignLeadModel,
    ContactConsentModel,
    ContactSuppressionModel,
    ConversationModel,
    ConversationTagModel,
    CrmDealModel,
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


class AnalyticsStoreMixin(BaseSqlAlchemyStore):
    @staticmethod
    def _qa_evaluation_from_model(m: QAEvaluationModel) -> QAEvaluation:
        return QAEvaluation(
            id=UUID(m.id),
            tenant_id=UUID(m.tenant_id),
            conversation_id=UUID(m.conversation_id),
            score=m.score,
            flags=m.flags,
            feedback=m.feedback,
            created_at=_timestamp(m.created_at),
            updated_at=_timestamp(m.updated_at),
        )

    @staticmethod
    def _weekly_report_from_model(m: WeeklyReportModel) -> WeeklyReport:
        return WeeklyReport(
            id=UUID(m.id),
            tenant_id=UUID(m.tenant_id),
            start_date=_timestamp(m.start_date),
            end_date=_timestamp(m.end_date),
            summary=m.summary,
            insights=m.insights,
            top_channels=m.top_channels,
            created_at=_timestamp(m.created_at),
            updated_at=_timestamp(m.updated_at),
        )

    @staticmethod
    def _test_case_from_model(model: TestCaseModel) -> TestCase:
        return TestCase(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            agent_id=UUID(model.agent_id),
            name=model.name,
            scenario=model.scenario,
            expected_outcome=model.expected_outcome,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    @staticmethod
    def _test_run_from_model(model: TestRunModel) -> TestRun:
        return TestRun(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            agent_id=UUID(model.agent_id),
            test_case_id=UUID(model.test_case_id),
            status=TestCaseStatus(model.status),
            logs=list(model.logs),
            result_summary=model.result_summary,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.updated_at),
        )

    def create_test_case(self, tenant_id: UUID, agent_id: UUID, payload: TestCaseCreate) -> TestCase:
        with self._session_scope() as session:
            model = TestCaseModel(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                agent_id=str(agent_id),
                name=payload.name,
                scenario=payload.scenario,
                expected_outcome=payload.expected_outcome,
            )
            session.add(model)
            session.flush()
            return self._test_case_from_model(model)

    def list_test_cases(self, tenant_id: UUID, agent_id: UUID) -> list[TestCase]:
        with self._session_scope() as session:
            models = session.scalars(
                select(TestCaseModel).where(
                    TestCaseModel.tenant_id == str(tenant_id),
                    TestCaseModel.agent_id == str(agent_id)
                )
            ).all()
            return [self._test_case_from_model(m) for m in models]

    def get_test_case(self, tenant_id: UUID, agent_id: UUID, test_case_id: UUID) -> TestCase | None:
        with self._session_scope() as session:
            model = session.get(TestCaseModel, str(test_case_id))
            if model and model.tenant_id == str(tenant_id) and model.agent_id == str(agent_id):
                return self._test_case_from_model(model)
            return None

    def create_test_run(self, tenant_id: UUID, agent_id: UUID, test_case_id: UUID) -> TestRun:
        with self._session_scope() as session:
            model = TestRunModel(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                agent_id=str(agent_id),
                test_case_id=str(test_case_id),
                status=TestCaseStatus.running.value,
                logs=[],
            )
            session.add(model)
            session.flush()
            return self._test_run_from_model(model)

    def update_test_run(self, tenant_id: UUID, agent_id: UUID, test_run_id: UUID, status: TestCaseStatus, logs: list[dict[str, object]], result_summary: str | None = None) -> TestRun | None:
        with self._session_scope() as session:
            model = session.get(TestRunModel, str(test_run_id))
            if not model or model.tenant_id != str(tenant_id) or model.agent_id != str(agent_id):
                return None
            model.status = status.value
            model.logs = list(logs)
            model.result_summary = result_summary
            model.updated_at = datetime.now(UTC)
            session.flush()
            return self._test_run_from_model(model)

    def list_test_runs(self, tenant_id: UUID, agent_id: UUID, test_case_id: UUID | None = None) -> list[TestRun]:
        with self._session_scope() as session:
            stmt = select(TestRunModel).where(
                TestRunModel.tenant_id == str(tenant_id),
                TestRunModel.agent_id == str(agent_id)
            )
            if test_case_id:
                stmt = stmt.where(TestRunModel.test_case_id == str(test_case_id))
            stmt = stmt.order_by(TestRunModel.created_at.desc())
            models = session.scalars(stmt).all()
            return [self._test_run_from_model(m) for m in models]

    # Inbox & Handoff
    def get_analytics_overview(self, tenant_id: UUID) -> dict[str, Any]:
        """Fetch optimized analytics overview directly via SQL."""
        with self._session_scope() as session:
            # Basic counts by status
            status_counts = session.execute(
                select(ConversationModel.status, func.count(ConversationModel.id))
                .where(ConversationModel.tenant_id == str(tenant_id))
                .group_by(ConversationModel.status)
            ).all()
            
            counts = {status: count for status, count in status_counts}
            resolved = counts.get("resolved", 0)
            escalated = counts.get("escalated", 0)
            open_count = counts.get("open", 0)
            total_conversations = sum(counts.values())
            automation_rate = (resolved / total_conversations * 100) if total_conversations > 0 else 0.0

            # Agents count
            total_agents = session.scalar(
                select(func.count(AgentModel.id))
                .where(AgentModel.tenant_id == str(tenant_id))
            ) or 0
            
            active_agents = session.scalar(
                select(func.count(AgentModel.id))
                .where(AgentModel.tenant_id == str(tenant_id))
                .where(AgentModel.status == "active")
            ) or 0

            # Knowledge sources count
            total_knowledge_sources = session.scalar(
                select(func.count(KnowledgeSourceModel.id))
                .where(KnowledgeSourceModel.tenant_id == str(tenant_id))
            ) or 0
            
            # Messages count
            total_messages = session.scalar(
                select(func.count(MessageModel.id))
                .where(MessageModel.tenant_id == str(tenant_id))
            ) or 0
            
            avg_messages_per_conversation = (total_messages / total_conversations) if total_conversations > 0 else 0.0

            # Channel breakdown
            channel_counts = session.execute(
                select(ConversationModel.channel, func.count(ConversationModel.id))
                .where(ConversationModel.tenant_id == str(tenant_id))
                .group_by(ConversationModel.channel)
            ).all()
            conversations_by_channel = [{"channel": ch, "count": c} for ch, c in channel_counts]

            thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
            recent_conversations = session.scalars(
                select(ConversationModel)
                .where(ConversationModel.tenant_id == str(tenant_id))
                .where(ConversationModel.created_at >= thirty_days_ago)
            ).all()
            
            from collections import Counter
            day_counts: Counter[str] = Counter()
            for rc in recent_conversations:
                day_str = rc.created_at.strftime("%Y-%m-%d")
                day_counts[day_str] += 1
                
            now = datetime.now(UTC)
            conversations_by_day = []
            for i in range(29, -1, -1):
                d = now - timedelta(days=i)
                d_str = d.strftime("%Y-%m-%d")
                conversations_by_day.append({"date": d_str, "count": day_counts[d_str]})
            
            # Revenue
            pipeline_value = session.scalar(
                select(func.sum(CrmDealModel.amount_minor))
                .where(CrmDealModel.tenant_id == str(tenant_id))
                .where(CrmDealModel.status.in_(["open", "negotiation", "won"]))
            ) or 0
            
            lost_revenue = session.scalar(
                select(func.sum(CrmDealModel.amount_minor))
                .where(CrmDealModel.tenant_id == str(tenant_id))
                .where(CrmDealModel.status == "lost")
            ) or 0
            
            return {
                "total_conversations": total_conversations,
                "resolved": resolved,
                "escalated": escalated,
                "open": open_count,
                "automation_rate": automation_rate,
                "total_agents": total_agents,
                "active_agents": active_agents,
                "total_knowledge_sources": total_knowledge_sources,
                "total_messages": total_messages,
                "avg_messages_per_conversation": avg_messages_per_conversation,
                "total_pipeline_value": float(pipeline_value) / 100.0,
                "estimated_lost_revenue": float(lost_revenue) / 100.0,
                "conversations_by_channel": conversations_by_channel,
                "conversations_by_day": conversations_by_day,
                "top_unresolved": [] # placeholder for now
            }

    def get_margin_dashboard(self, tenant_id: UUID) -> dict[str, Any]:
        """Fetch margin dashboard stats (Revenue vs Costs)."""
        with self._session_scope() as session:
            # Revenue = Sum of all won deals
            revenue = session.scalar(
                select(func.sum(CrmDealModel.amount_minor))
                .where(CrmDealModel.tenant_id == str(tenant_id))
                .where(CrmDealModel.status == "won")
            ) or 0

            # Costs = Sum of all billing ledger entries (where type is usage and amount is positive)
            costs = session.scalar(
                select(func.sum(BillingLedgerEntryModel.amount_minor))
                .where(BillingLedgerEntryModel.tenant_id == str(tenant_id))
                .where(BillingLedgerEntryModel.amount_minor > 0)
            ) or 0

            margin = revenue - costs
            margin_percentage = (margin / revenue * 100) if revenue > 0 else 0.0

            return {
                "total_revenue_minor": revenue,
                "total_costs_minor": costs,
                "margin_minor": margin,
                "margin_percentage": margin_percentage,
                "currency": "RUB"
            }

    def save_qa_evaluation(self, evaluation: QAEvaluation) -> None:
        model = QAEvaluationModel(
            id=str(evaluation.id),
            tenant_id=str(evaluation.tenant_id),
            conversation_id=str(evaluation.conversation_id),
            score=evaluation.score,
            flags=evaluation.flags,
            feedback=evaluation.feedback,
        )
        with self._session_scope() as session:
            session.add(model)

    def get_qa_evaluations(self, tenant_id: UUID, conversation_id: UUID) -> list[QAEvaluation]:
        with self._session_scope() as session:
            models = session.scalars(
                select(QAEvaluationModel)
                .where(QAEvaluationModel.tenant_id == str(tenant_id))
                .where(QAEvaluationModel.conversation_id == str(conversation_id))
            ).all()
            return [self._qa_evaluation_from_model(m) for m in models]

    def save_weekly_report(self, report: WeeklyReport) -> None:
        model = WeeklyReportModel(
            id=str(report.id),
            tenant_id=str(report.tenant_id),
            start_date=report.start_date,
            end_date=report.end_date,
            summary=report.summary,
            insights=report.insights,
            top_channels=report.top_channels,
        )
        with self._session_scope() as session:
            session.add(model)

    def list_weekly_reports(self, tenant_id: UUID) -> list[WeeklyReport]:
        with self._session_scope() as session:
            models = session.scalars(
                select(WeeklyReportModel)
                .where(WeeklyReportModel.tenant_id == str(tenant_id))
                .order_by(WeeklyReportModel.created_at.desc())
            ).all()
            return [self._weekly_report_from_model(m) for m in models]

