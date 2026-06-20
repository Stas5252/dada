from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import require_tenant_permission
from app.rbac import Permission
from app.schemas import Agent, AgentCreateRequest, AgentUpdateRequest
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
