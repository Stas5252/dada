from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.dependencies import require_tenant_permission
from app.channels.telegram_adapter import TelegramChannelAdapter
from app.encryption import encrypt_token
from app.policy_validator import PolicyValidationError, PromptPolicyValidator
from app.rbac import Permission
from app.schemas import Agent, AgentCreateRequest, AgentUpdateRequest, TelegramConnectRequest
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

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
    try:
        PromptPolicyValidator.validate_prompt(payload.prompt)
    except PolicyValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return app_store.create_agent(UUID(tenant_id), payload)


@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdateRequest,
    tenant_id: str = Depends(MANAGE_AGENTS),
    app_store: AppStore = Depends(get_app_store),
) -> Agent:
    if payload.prompt is not None:
        try:
            PromptPolicyValidator.validate_prompt(payload.prompt)
        except PolicyValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

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

    adapter = TelegramChannelAdapter(bot_token=payload.bot_token)
    webhook_url = f"{settings.api_public_url}/api/v1/webhooks/telegram/{agent_id}"

    import hashlib
    secret_token = hashlib.sha256(payload.bot_token.encode("utf-8")).hexdigest()

    success = await adapter.set_webhook(webhook_url, secret_token=secret_token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to connect Telegram Bot. Token might be invalid.",
        )

    encrypted_token = encrypt_token(payload.bot_token, settings.access_token_secret)
    update_request = AgentUpdateRequest(telegram_bot_token=encrypted_token)
    updated_agent = app_store.update_agent(UUID(tenant_id), agent_id, update_request)

    if not updated_agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found during update")

    return updated_agent


class PathwayResponse(BaseModel):
    nodes: list[dict[str, object]] | None = None
    edges: list[dict[str, object]] | None = None


@router.get("/{agent_id}/pathway", response_model=PathwayResponse)
async def get_agent_pathway(
    agent_id: UUID,
    tenant_id: str = Depends(READ_AGENTS),
    app_store: AppStore = Depends(get_app_store),
) -> PathwayResponse:
    agent = app_store.get_agent(UUID(tenant_id), agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return PathwayResponse(nodes=agent.pathway_nodes, edges=agent.pathway_edges)


class SavePathwayRequest(BaseModel):
    nodes: list[dict[str, object]]
    edges: list[dict[str, object]]


def _pathway_node_label(node: dict[str, object]) -> str:
    data = node.get("data")
    if not isinstance(data, dict):
        return ""
    return str(data.get("label", "")).lower()


@router.post("/{agent_id}/pathway", response_model=PathwayResponse)
async def save_agent_pathway(
    agent_id: UUID,
    payload: SavePathwayRequest,
    tenant_id: str = Depends(MANAGE_AGENTS),
    app_store: AppStore = Depends(get_app_store),
) -> PathwayResponse:
    agent = app_store.get_agent(UUID(tenant_id), agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    has_start = any(
        n.get("type") == "input"
        or n.get("id") == "1"
        or "start" in _pathway_node_label(n)
        for n in payload.nodes
    )
    if not has_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing start node (Start).",
        )

    update_req = AgentUpdateRequest(
        pathway_nodes=payload.nodes,
        pathway_edges=payload.edges,
    )
    updated_agent = app_store.update_agent(UUID(tenant_id), agent_id, update_req)
    if not updated_agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found during update")

    return PathwayResponse(nodes=updated_agent.pathway_nodes, edges=updated_agent.pathway_edges)
