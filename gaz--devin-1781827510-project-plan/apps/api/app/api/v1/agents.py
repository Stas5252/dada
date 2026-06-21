from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import require_tenant_permission
from app.rbac import Permission
from app.schemas import Agent, AgentCreateRequest, AgentUpdateRequest, TelegramConnectRequest
from app.store_factory import AppStore, get_app_store
from app.settings import Settings, get_settings
from app.encryption import encrypt_token
from app.channels.telegram_adapter import TelegramChannelAdapter

router = APIRouter(prefix="/agents", tags=["agents"])
READ_AGENTS = require_tenant_permission(Permission.READ_AGENTS)
MANAGE_AGENTS = require_tenant_permission(Permission.MANAGE_AGENTS)


@router.get("", response_model=list[Agent])
async def list_agents(
    tenant_id: str = Depends(READ_AGENTS),
    app_store: AppStore = Depends(get_app_store),
) -> list[Agent]:
    return app_store.list_agents(UUID(tenant_id))


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: UUID,
    tenant_id: str = Depends(READ_AGENTS),
    app_store: AppStore = Depends(get_app_store),
) -> Agent:
    agent = app_store.get_agent(UUID(tenant_id), agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.post("", response_model=Agent, status_code=201)
async def create_agent(
    payload: AgentCreateRequest,
    tenant_id: str = Depends(MANAGE_AGENTS),
    app_store: AppStore = Depends(get_app_store),
) -> Agent:
    return app_store.create_agent(UUID(tenant_id), payload)


@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdateRequest,
    tenant_id: str = Depends(MANAGE_AGENTS),
    app_store: AppStore = Depends(get_app_store),
) -> Agent:
    agent = app_store.update_agent(UUID(tenant_id), agent_id, payload)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.post("/{agent_id}/publish", response_model=Agent)
async def publish_agent(
    agent_id: UUID,
    tenant_id: str = Depends(MANAGE_AGENTS),
    app_store: AppStore = Depends(get_app_store),
) -> Agent:
    agent = app_store.publish_agent(UUID(tenant_id), agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent

@router.post("/{agent_id}/telegram/connect", response_model=Agent)
async def connect_telegram(
    agent_id: UUID,
    payload: TelegramConnectRequest,
    tenant_id: str = Depends(MANAGE_AGENTS),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> Agent:
    agent = app_store.get_agent(UUID(tenant_id), agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    # Instantiate adapter with the provided token to test and set webhook
    adapter = TelegramChannelAdapter(bot_token=payload.bot_token)
    webhook_url = f"{settings.api_public_url}/api/v1/webhooks/telegram/{agent_id}"
    
    success = await adapter.set_webhook(webhook_url)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to connect Telegram Bot. Token might be invalid.")

    # Encrypt the token before saving
    encrypted_token = encrypt_token(payload.bot_token, settings.access_token_secret)
    
    # Update agent with new encrypted token
    update_request = AgentUpdateRequest(telegram_bot_token=encrypted_token)
    updated_agent = app_store.update_agent(UUID(tenant_id), agent_id, update_request)
    
    if not updated_agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found during update")
        
    return updated_agent
