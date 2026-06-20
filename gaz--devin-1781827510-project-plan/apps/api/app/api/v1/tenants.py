from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.dependencies import require_tenant_permission
from app.rbac import Permission
from app.schemas import DashboardResponse
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/tenants", tags=["tenants"])
READ_DASHBOARD = require_tenant_permission(Permission.READ_CHAT)


@router.get("/{tenant_id}/dashboard", response_model=DashboardResponse)
async def dashboard(
    tenant_id: UUID,
    current_tenant_id: str = Depends(READ_DASHBOARD),
    app_store: AppStore = Depends(get_app_store),
) -> DashboardResponse:
    if str(tenant_id) != current_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant = app_store.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    agents = app_store.list_agents(tenant_id)
    sources = app_store.list_knowledge_sources(tenant_id)
    conversations = app_store.list_conversations(tenant_id)
    resolved = [
        conversation
        for conversation in conversations
        if conversation.resolution_status == "resolved"
    ]
    automation_rate = len(resolved) / len(conversations) if conversations else 0
    return DashboardResponse(
        tenant=tenant,
        agents_total=len(agents),
        knowledge_sources_total=len(sources),
        conversations_total=len(conversations),
        unresolved_topics_total=len(conversations) - len(resolved),
        automation_rate=automation_rate,
    )


class TenantSettingsUpdate(BaseModel):
    settings: dict[str, object]


MANAGE_TENANT = require_tenant_permission(Permission.MANAGE_CHAT)


@router.get("/{tenant_id}/settings")
async def get_tenant_settings(
    tenant_id: UUID,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, object]:
    if str(tenant_id) != current_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant = app_store.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant.settings


@router.post("/{tenant_id}/settings")
async def update_tenant_settings_endpoint(
    tenant_id: UUID,
    payload: TenantSettingsUpdate,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, object]:
    if str(tenant_id) != current_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    updated = app_store.update_tenant_settings(tenant_id, payload.settings)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return updated.settings
