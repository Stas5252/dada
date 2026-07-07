from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.dependencies import require_tenant_permission
from app.channel_policy import (
    audit_channel_policy_consent_block,
    audit_channel_policy_outbound_block,
    channel_policy_for_settings,
)
from app.channels import ChannelType, OutboundMessage
from app.channels.telegram_adapter import TelegramChannelAdapter
from app.orchestrator import AgentOrchestrator
from app.rbac import Permission
from app.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ContactConsent,
    ContactConsentCreateRequest,
    ContactSuppression,
    ContactSuppressionCreateRequest,
    Conversation,
    ConversationDetail,
    Message,
)
from app.service_factory import get_telegram_adapter
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(tags=["conversations"])
READ_CHAT = require_tenant_permission(Permission.READ_CHAT)
MANAGE_CHAT = require_tenant_permission(Permission.MANAGE_CHAT)


@router.get("/conversations", response_model=list[Conversation])
async def list_conversations(
    search: str | None = None,
    status: str | None = None,
    channel: str | None = None,
    tenant_id: str = Depends(READ_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> list[Conversation]:
    return app_store.list_conversations(
        UUID(tenant_id), search=search, status=status, channel=channel
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    tenant_id: str = Depends(READ_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> ConversationDetail:
    detail = app_store.get_conversation_detail(UUID(tenant_id), conversation_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    conversation, messages, sources = detail
    return ConversationDetail(conversation=conversation, messages=messages, sources=sources)


@router.post("/chat/mock", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def mock_chat(
    payload: ChatMessageRequest,
    tenant_id: str = Depends(MANAGE_CHAT),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> ChatMessageResponse:
    from app.api.v1.dependencies import check_billing_limit

    check_billing_limit(UUID(tenant_id), app_store, source="chat_mock")

    # 1. Ask orchestrator for dynamic response
    from app.service_factory import get_agent_orchestrator
    orchestrator = get_agent_orchestrator()

    # Use provided conversation_id or generate a new one
    from uuid import uuid4

    conversation_id = payload.conversation_id if payload.conversation_id else uuid4()

    orchestrator_result = await orchestrator.process_message(
        tenant_id=UUID(tenant_id),
        agent_id=payload.agent_id,
        conversation_id=conversation_id,
        customer_message=payload.message,
        channel=payload.channel,
    )
    response_text = orchestrator_result.response_text

    # 2. Persist using store with dynamic text
    payload_with_conversation = payload.model_copy(update={"conversation_id": conversation_id})
    answer = app_store.answer_chat(
        UUID(tenant_id),
        payload_with_conversation,
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score,
        forced_status=orchestrator_result.forced_status,
        forced_resolution_status=orchestrator_result.forced_resolution_status,
        retrieval_results=orchestrator_result.retrieval_results,
    )
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    conversation, customer_message, agent_message, sources = answer
    return ChatMessageResponse(
        conversation=conversation,
        customer_message=customer_message,
        agent_message=agent_message,
        sources=sources,
    )


class OperatorMessageRequest(BaseModel):
    content: str


@router.post("/conversations/{conversation_id}/messages", response_model=Message)
async def send_operator_message(
    conversation_id: UUID,
    payload: OperatorMessageRequest,
    tenant_id: str = Depends(MANAGE_CHAT),
    app_store: AppStore = Depends(get_app_store),
    telegram: TelegramChannelAdapter = Depends(get_telegram_adapter),
) -> Message:
    conversation = app_store.get_conversation(UUID(tenant_id), conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    channel_policy = channel_policy_for_settings(
        tenant.settings if tenant else None,
        conversation.channel,
    )
    if not channel_policy.outbound_enabled:
        audit_channel_policy_outbound_block(
            app_store,
            tenant_id=tenant_uuid,
            channel=conversation.channel,
            conversation_id=conversation_id,
            source="operator_message",
            policy=channel_policy,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Outbound messages are disabled by channel policy",
        )

    customer = (
        app_store.get_customer(tenant_uuid, conversation.customer_id)
        if conversation.customer_id
        else None
    )
    if customer:
        suppression = app_store.find_contact_suppression(
            tenant_uuid,
            conversation.channel,
            external_id=customer.external_id,
            phone=customer.phone,
        )
        if suppression:
            app_store.create_audit_log(
                event_type="contact_suppression.outbound_blocked",
                tenant_id=tenant_uuid,
                details={
                    "channel": conversation.channel,
                    "contact_type": suppression.contact_type,
                    "conversation_id": str(conversation_id),
                    "source": "operator_message",
                    "suppression_id": str(suppression.id),
                    "value": suppression.value,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Contact has opted out of outbound messages",
            )

    if channel_policy.require_contact_consent_for_outbound:
        consent = (
            app_store.find_contact_consent(
                tenant_uuid,
                conversation.channel,
                external_id=customer.external_id,
                phone=customer.phone,
            )
            if customer
            else None
        )
        if not consent:
            contact_type = "external_id" if customer and customer.external_id else None
            value = customer.external_id if customer and customer.external_id else None
            audit_channel_policy_consent_block(
                app_store,
                tenant_id=tenant_uuid,
                channel=conversation.channel,
                conversation_id=conversation_id,
                source="operator_message",
                policy=channel_policy,
                contact_type=contact_type,
                value=value,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Outbound consent is required by channel policy",
            )

    message = app_store.add_operator_message(
        tenant_uuid, conversation_id, payload.content
    )
    if not message:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.channel == "telegram" and customer and customer.external_id:
        outbound = OutboundMessage(
            channel=ChannelType.telegram,
            external_chat_id=customer.external_id,
            text=payload.content,
        )
        await telegram.send_message(outbound)

    return message


@router.post("/conversations/{conversation_id}/resolve", response_model=Conversation)
async def resolve_conversation(
    conversation_id: UUID,
    tenant_id: str = Depends(MANAGE_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> Conversation:
    conversation = app_store.resolve_conversation(UUID(tenant_id), conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/contact-suppressions", response_model=list[ContactSuppression])
async def list_contact_suppressions(
    tenant_id: str = Depends(READ_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> list[ContactSuppression]:
    return app_store.list_contact_suppressions(UUID(tenant_id))


@router.post(
    "/contact-suppressions",
    response_model=ContactSuppression,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact_suppression(
    payload: ContactSuppressionCreateRequest,
    tenant_id: str = Depends(MANAGE_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> ContactSuppression:
    try:
        return app_store.record_contact_suppression(
            UUID(tenant_id),
            payload.channel,
            payload.contact_type,
            payload.value,
            reason=payload.reason,
            source=payload.source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/contact-suppressions/{suppression_id}", response_model=ContactSuppression)
async def revoke_contact_suppression(
    suppression_id: UUID,
    tenant_id: str = Depends(MANAGE_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> ContactSuppression:
    suppression = app_store.revoke_contact_suppression(UUID(tenant_id), suppression_id)
    if not suppression:
        raise HTTPException(status_code=404, detail="Contact suppression not found")
    return suppression


@router.get("/contact-consents", response_model=list[ContactConsent])
async def list_contact_consents(
    tenant_id: str = Depends(READ_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> list[ContactConsent]:
    return app_store.list_contact_consents(UUID(tenant_id))


@router.post(
    "/contact-consents",
    response_model=ContactConsent,
    status_code=status.HTTP_201_CREATED,
)
async def create_contact_consent(
    payload: ContactConsentCreateRequest,
    tenant_id: str = Depends(MANAGE_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> ContactConsent:
    try:
        return app_store.record_contact_consent(
            UUID(tenant_id),
            payload.channel,
            payload.contact_type,
            payload.value,
            consent_type=payload.consent_type,
            source=payload.source,
            expires_at=payload.expires_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/contact-consents/{consent_id}", response_model=ContactConsent)
async def revoke_contact_consent(
    consent_id: UUID,
    tenant_id: str = Depends(MANAGE_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> ContactConsent:
    consent = app_store.revoke_contact_consent(UUID(tenant_id), consent_id)
    if not consent:
        raise HTTPException(status_code=404, detail="Contact consent not found")
    return consent


@router.post("/conversations/{conversation_id}/handoff", response_model=Conversation)
async def handoff_conversation(
    conversation_id: UUID,
    tenant_id: str = Depends(MANAGE_CHAT),
    app_store: AppStore = Depends(get_app_store),
) -> Conversation:
    conversation = app_store.escalate_conversation(UUID(tenant_id), conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
