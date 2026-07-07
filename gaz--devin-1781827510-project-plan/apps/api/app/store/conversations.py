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


class ConversationsStoreMixin(BaseSqlAlchemyStore):
    def list_conversations(
        self,
        tenant_id: UUID,
        search: str | None = None,
        status: str | None = None,
        channel: str | None = None,
    ) -> list[Conversation]:
        with self._session_scope() as session:
            stmt = select(ConversationModel).where(ConversationModel.tenant_id == str(tenant_id))
            if status:
                stmt = stmt.where(ConversationModel.status == status)
            if channel:
                stmt = stmt.where(ConversationModel.channel == channel)
            if search:
                stmt = stmt.where(ConversationModel.summary.ilike(f"%{search}%"))
            conversation_models = session.scalars(stmt).all()
            return [self._conversation_from_model(model) for model in conversation_models]

    def count_messages(self, tenant_id: UUID, since: datetime | None = None) -> int:
        with self._session_scope() as session:
            stmt = select(func.count(MessageModel.id)).where(
                MessageModel.tenant_id == str(tenant_id)
            )
            if since is not None:
                stmt = stmt.where(MessageModel.created_at >= since)
            return session.scalar(stmt) or 0

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
        confidence_score: float | None = None,
        forced_status: ConversationStatus | None = None,
        forced_resolution_status: str | None = None,
        retrieval_results: list[Any] | None = None,
    ) -> tuple[Conversation, Message, Message, list[KnowledgeSource]] | None:
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
            retrieval_results=retrieval_results,
        )

    def record_chat_turn_background(
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
    ) -> None:
        import asyncio
        asyncio.create_task(
            asyncio.to_thread(
                self.record_chat_turn,
                tenant_id,
                agent_id,
                conversation_id,
                channel,
                customer_text,
                agent_response_text,
                customer_id,
                confidence_score,
                forced_status,
                forced_resolution_status,
            )
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
        agent = self.get_agent(tenant_id, agent_id)
        if agent is None:
            return None

        # Visual Pathway Graph interpretation fallback
        if agent_response_text is None:
            with self._session_scope() as session:
                message_models = session.scalars(
                    select(MessageModel).where(MessageModel.conversation_id == str(conversation_id))
                ).all()
                previous_messages = [self._message_from_model(m) for m in message_models]
            from app.scenario_engine import interpret_pathway
            pathway_response = interpret_pathway(agent, previous_messages, customer_text)
            if pathway_response:
                agent_response_text = pathway_response

        payload = ChatMessageRequest(agent_id=agent_id, channel=channel, message=customer_text)

        source_ids = []
        if retrieval_results:
            source_ids = [res.source_id for res in retrieval_results]

        status_value = ConversationStatus.open if forced_status is None else forced_status
        resolution_status = "resolved" if forced_resolution_status is None else forced_resolution_status

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
            content=agent_response_text if agent_response_text else "Извините, не удалось сформировать ответ.",
            confidence=confidence_score if confidence_score is not None else 0.2,
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
                conversation_model.summary = conversation_model.summary or customer_text[:120]
                conversation_model.resolution_status = resolution_status
                if customer_id is not None:
                    conversation_model.customer_id = str(customer_id)
            else:
                conversation_model = ConversationModel(
                    id=str(conversation_id),
                    tenant_id=str(tenant_id),
                    agent_id=str(agent_id),
                    customer_id=str(customer_id) if customer_id else None,
                    channel=channel,
                    status=status_value,
                    summary=customer_text[:120],
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
            
            sources = []
            if source_ids:
                source_models = session.scalars(
                    select(KnowledgeSourceModel).where(KnowledgeSourceModel.id.in_([str(sid) for sid in source_ids]))
                ).all()
                sources = [self._knowledge_source_from_model(sm) for sm in source_models]
                
        return (
            conversation,
            customer_message,
            agent_message,
            sources,
        )

    def get_conversation_detail(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
    ) -> tuple[Conversation, list[Message], list[KnowledgeSource]] | None:
        with self._session_scope() as session:
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

    def add_operator_message(
        self, tenant_id: UUID, conversation_id: UUID, content: str
    ) -> Message | None:
        with self._session_scope() as session:
            conversation_model = session.get(ConversationModel, str(conversation_id))
            if conversation_model is None or conversation_model.tenant_id != str(tenant_id):
                return None

            message = Message(
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                role=MessageRole.operator,
                content=content,
                source_ids=[],
            )
            session.add(self._message_to_model(message))
            
            return message

    def run_agent_workflow(
        self, tenant_id: UUID, task_payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        raise NotImplementedError

    def resolve_conversation(
        self, tenant_id: UUID, conversation_id: UUID
    ) -> Conversation | None:
        with self._session_scope() as session:
            conversation_model = session.get(ConversationModel, str(conversation_id))
            if conversation_model is None or conversation_model.tenant_id != str(tenant_id):
                return None

            conversation_model.status = ConversationStatus.resolved
            conversation_model.resolution_status = "Resolved by operator"
            
            return self._conversation_from_model(conversation_model)

    def escalate_conversation(
        self, tenant_id: UUID, conversation_id: UUID
    ) -> Conversation | None:
        with self._session_scope() as session:
            conversation_model = session.get(ConversationModel, str(conversation_id))
            if conversation_model is None or conversation_model.tenant_id != str(tenant_id):
                return None

            conversation_model.status = ConversationStatus.escalated
            conversation_model.resolution_status = "Escalated to human operator"

            return self._conversation_from_model(conversation_model)

    def update_conversation_summary(
        self, tenant_id: UUID, conversation_id: UUID, summary: str
    ) -> Conversation | None:
        with self._session_scope() as session:
            conversation_model = session.get(ConversationModel, str(conversation_id))
            if conversation_model is None or conversation_model.tenant_id != str(tenant_id):
                return None

            conversation_model.summary = summary
            return self._conversation_from_model(conversation_model)

    def get_conversation(self, tenant_id: UUID, conversation_id: UUID) -> Conversation | None:
        with self._session_scope() as session:
            conversation_model = session.get(ConversationModel, str(conversation_id))
            if conversation_model is None or conversation_model.tenant_id != str(tenant_id):
                return None
            return self._conversation_from_model(conversation_model)

    @staticmethod
    def _conversation_from_model(model: ConversationModel) -> Conversation:
        return Conversation(
            id=UUID(model.id),
            tenant_id=UUID(model.tenant_id),
            agent_id=UUID(model.agent_id),
            customer_id=UUID(model.customer_id) if model.customer_id else None,
            channel=model.channel,
            status=ConversationStatus(model.status),
            summary=model.summary,
            resolution_status=model.resolution_status,
            priority=model.priority,
            sla_due_at=_timestamp(model.sla_due_at) if model.sla_due_at else None,
            handoff_status=model.handoff_status,
            assigned_user_id=UUID(model.assigned_user_id) if model.assigned_user_id else None,
            created_at=_timestamp(model.created_at),
            updated_at=_timestamp(model.created_at),
        )

    @staticmethod
    def _inbox_conversation_from_model(session: Session, model: ConversationModel) -> InboxConversation:
        tags = [t.tag_name for t in session.scalars(
            select(ConversationTagModel).where(ConversationTagModel.conversation_id == model.id)
        )]
        return InboxConversation(
            id=model.id,
            tenant_id=model.tenant_id,
            agent_id=model.agent_id,
            customer_id=model.customer_id,
            channel=model.channel,
            status=model.status,
            summary=model.summary,
            resolution_status=model.resolution_status,
            created_at=model.created_at,
            priority=model.priority,
            sla_due_at=model.sla_due_at,
            handoff_status=model.handoff_status,
            assigned_user_id=model.assigned_user_id,
            tags=tags
        )

    @staticmethod
    def _conversation_tag_from_model(model: ConversationTagModel) -> ConversationTag:
        return ConversationTag(
            id=model.id,
            tenant_id=model.tenant_id,
            conversation_id=model.conversation_id,
            tag_name=model.tag_name,
            created_at=model.created_at
        )

    @staticmethod
    def _internal_note_from_model(model: InternalNoteModel) -> InternalNote:
        return InternalNote(
            id=model.id,
            tenant_id=model.tenant_id,
            conversation_id=model.conversation_id,
            body=model.body,
            author_user_id=model.author_user_id,
            created_at=model.created_at,
            updated_at=model.updated_at
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

    def list_inbox_conversations(
        self,
        tenant_id: UUID,
        handoff_status: str | None = None,
        assigned_user_id: str | None = None
    ) -> list[InboxConversation]:
        with self._session_scope() as session:
            stmt = select(ConversationModel).where(ConversationModel.tenant_id == str(tenant_id))
            if handoff_status:
                stmt = stmt.where(ConversationModel.handoff_status == handoff_status)
            if assigned_user_id:
                stmt = stmt.where(ConversationModel.assigned_user_id == assigned_user_id)
            stmt = stmt.order_by(ConversationModel.created_at.desc())
            models = session.scalars(stmt).all()
            return [self._inbox_conversation_from_model(session, m) for m in models]

    def assign_conversation(
        self, tenant_id: UUID, conversation_id: str, user_id: str
    ) -> InboxConversation | None:
        with self._session_scope() as session:
            conv = session.get(ConversationModel, conversation_id)
            if not conv or conv.tenant_id != str(tenant_id):
                return None
            conv.assigned_user_id = user_id
            conv.handoff_status = "assigned"
            
            # create assignment record
            assignment = HandoffAssignmentModel(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                conversation_id=conversation_id,
                user_id=user_id,
                status="active"
            )
            session.add(assignment)
            
            # unassign previous if exists
            prev_assignments = session.scalars(
                select(HandoffAssignmentModel).where(
                    HandoffAssignmentModel.conversation_id == conversation_id,
                    HandoffAssignmentModel.status == "active",
                    HandoffAssignmentModel.id != assignment.id
                )
            ).all()
            now = datetime.now(UTC)
            for pa in prev_assignments:
                pa.status = "completed"
                pa.unassigned_at = now
            session.flush()
            return self._inbox_conversation_from_model(session, conv)

    def return_conversation_to_ai(
        self, tenant_id: UUID, conversation_id: str
    ) -> InboxConversation | None:
        with self._session_scope() as session:
            conv = session.get(ConversationModel, conversation_id)
            if not conv or conv.tenant_id != str(tenant_id):
                return None
            conv.assigned_user_id = None
            conv.handoff_status = "ai_handling"
            
            # unassign previous if exists
            prev_assignments = session.scalars(
                select(HandoffAssignmentModel).where(
                    HandoffAssignmentModel.conversation_id == conversation_id,
                    HandoffAssignmentModel.status == "active"
                )
            ).all()
            now = datetime.now(UTC)
            for pa in prev_assignments:
                pa.status = "completed"
                pa.unassigned_at = now
            session.flush()
            return self._inbox_conversation_from_model(session, conv)

    def add_conversation_tag(
        self, tenant_id: UUID, conversation_id: str, tag_name: str
    ) -> ConversationTag | None:
        with self._session_scope() as session:
            # check if exists
            existing = session.scalar(
                select(ConversationTagModel).where(
                    ConversationTagModel.conversation_id == conversation_id,
                    ConversationTagModel.tag_name == tag_name
                )
            )
            if existing:
                return self._conversation_tag_from_model(existing)
                
            model = ConversationTagModel(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                conversation_id=conversation_id,
                tag_name=tag_name
            )
            session.add(model)
            session.flush()
            return self._conversation_tag_from_model(model)

    def remove_conversation_tag(
        self, tenant_id: UUID, conversation_id: str, tag_name: str
    ) -> bool:
        with self._session_scope() as session:
            model = session.scalar(
                select(ConversationTagModel).where(
                    ConversationTagModel.tenant_id == str(tenant_id),
                    ConversationTagModel.conversation_id == conversation_id,
                    ConversationTagModel.tag_name == tag_name
                )
            )
            if model:
                session.delete(model)
                return True
            return False

    def add_internal_note(
        self, tenant_id: UUID, conversation_id: str, body: str, author_user_id: str | None = None
    ) -> InternalNote | None:
        with self._session_scope() as session:
            model = InternalNoteModel(
                id=str(uuid4()),
                tenant_id=str(tenant_id),
                conversation_id=conversation_id,
                body=body,
                author_user_id=author_user_id
            )
            session.add(model)
            session.flush()
            return self._internal_note_from_model(model)

