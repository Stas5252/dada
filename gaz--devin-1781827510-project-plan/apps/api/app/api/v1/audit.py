from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import require_tenant_permission
from app.rbac import Permission
from app.schemas import AuditLog
from app.store_factory import AppStore, get_app_store

router = APIRouter(tags=["audit"])
READ_AUDIT = require_tenant_permission(Permission.READ_AUDIT)


@router.get("/audit-logs", response_model=list[AuditLog])
async def list_audit_logs(
    tenant_id: str = Depends(READ_AUDIT),
    app_store: AppStore = Depends(get_app_store),
) -> list[AuditLog]:
    return app_store.list_audit_logs(UUID(tenant_id))
