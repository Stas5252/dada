from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import require_tenant_permission
from app.orchestrator import AgentOrchestrator
from app.rbac import Permission
from app.schemas import ChatMessageRequest, ChatMessageResponse, Conversation, ConversationDetail
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

    # Generate a temporary conversation id for orchestrator context.
    # Mock chat currently creates a new conversation each time.
    from uuid import uuid4

    conversation_id = uuid4()

    response_text = await orchestrator.process_message(
        tenant_id=UUID(tenant_id),
        agent_id=payload.agent_id,
        conversation_id=conversation_id,
        customer_message=payload.message,
        channel=payload.channel,
    )

    # 2. Persist using store with dynamic text
    answer = app_store.answer_chat(UUID(tenant_id), payload, agent_response_text=response_text)
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    conversation, customer_message, agent_message, sources = answer
    return ChatMessageResponse(
        conversation=conversation,
        customer_message=customer_message,
        agent_message=agent_message,
        sources=sources,
    )
