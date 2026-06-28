from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.dependencies import require_tenant_permission
from app.channels import ChannelType, OutboundMessage
from app.channels.telegram_adapter import TelegramChannelAdapter
from app.orchestrator import AgentOrchestrator
from app.rbac import Permission
from app.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
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

    check_billing_limit(UUID(tenant_id), app_store)

    # 1. Ask orchestrator for dynamic response
    orchestrator = AgentOrchestrator(store=app_store, settings=settings)

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
    answer = app_store.answer_chat(
        UUID(tenant_id), 
        payload, 
        agent_response_text=response_text,
        confidence_score=orchestrator_result.confidence_score
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

    message = app_store.add_operator_message(
        UUID(tenant_id), conversation_id, payload.content
    )
    if not message:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.channel == "telegram" and conversation.customer_id:
        customer = app_store.get_customer(UUID(tenant_id), conversation.customer_id)
        if customer and customer.external_id:
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
