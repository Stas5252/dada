"""
Super Admin API endpoints.
Platform-wide tenant management for super_admin users.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.dependencies import AuthContext, require_permission
from app.rbac import Permission
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/admin", tags=["admin"])

# Only owners can access admin endpoints (we'll check for super_admin below)
READ_ADMIN = require_permission(Permission.READ_AUDIT)


class TenantOverview(BaseModel):
    id: str
    name: str
    plan: str
    status: str
    agents_count: int
    conversations_count: int
    messages_count: int


class AdminDashboard(BaseModel):
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    total_agents: int
    total_conversations: int
    total_messages: int


def _require_super_admin(auth: AuthContext) -> None:
    if not auth.user.email.endswith("@callforce.ru") and auth.user.email != "admin@example.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )


@router.get("/tenants", response_model=list[TenantOverview])
async def list_all_tenants(
    auth: AuthContext = Depends(READ_ADMIN),
    app_store: AppStore = Depends(get_app_store),
) -> list[TenantOverview]:
    """List all tenants with summary metrics. Super admin only."""
    _require_super_admin(auth)
    
    tenants = app_store.list_all_tenants()
    result: list[TenantOverview] = []
    for tenant in tenants:
        tid = tenant.id
        agents = app_store.list_agents(tid)
        conversations = app_store.list_conversations(tid)
        messages = app_store.count_messages(tid)
        result.append(
            TenantOverview(
                id=str(tid),
                name=tenant.name,
                plan=tenant.plan,
                status=tenant.status if hasattr(tenant, "status") else "active",
                agents_count=len(agents),
                conversations_count=len(conversations),
                messages_count=messages,
            )
        )
    return result


@router.get("/overview", response_model=AdminDashboard)
async def admin_overview(
    auth: AuthContext = Depends(READ_ADMIN),
    app_store: AppStore = Depends(get_app_store),
) -> AdminDashboard:
    """Global platform KPIs for super admin dashboard."""
    _require_super_admin(auth)
    
    tenants = app_store.list_all_tenants()
    total_agents = 0
    total_conversations = 0
    total_messages = 0
    active = 0
    suspended = 0

    for tenant in tenants:
        tid = tenant.id
        status_val = getattr(tenant, "status", "active")
        if status_val == "active":
            active += 1
        elif status_val == "suspended":
            suspended += 1
        else:
            active += 1

        total_agents += len(app_store.list_agents(tid))
        total_conversations += len(app_store.list_conversations(tid))
        total_messages += app_store.count_messages(tid)

    return AdminDashboard(
        total_tenants=len(tenants),
        active_tenants=active,
        suspended_tenants=suspended,
        total_agents=total_agents,
        total_conversations=total_conversations,
        total_messages=total_messages,
    )


class TenantStatusUpdate(BaseModel):
    status: str


@router.post("/tenants/{tenant_id}/status")
async def update_tenant_status(
    tenant_id: str,
    payload: TenantStatusUpdate,
    auth: AuthContext = Depends(READ_ADMIN),
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, str]:
    """Suspend or activate a tenant."""
    _require_super_admin(auth)
    
    tid = UUID(tenant_id)
    tenant = app_store.get_tenant(tid)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if payload.status not in ("active", "suspended"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'active' or 'suspended'",
        )

    app_store.update_tenant_settings(tid, {"status": payload.status})
    return {"tenant_id": tenant_id, "status": payload.status}
