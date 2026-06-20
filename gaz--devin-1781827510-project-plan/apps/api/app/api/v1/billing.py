from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import require_tenant_permission
from app.billing_service import BillingService
from app.contracts.billing import BillingLedgerEntry
from app.contracts.types import JsonValue
from app.rbac import Permission
from app.service_factory import get_billing_service
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/billing", tags=["billing"])
# Enable read access for chat users as well.
MANAGE_BILLING = require_tenant_permission(Permission.READ_CHAT)


class UsageChargeRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    payload: dict[str, JsonValue]


@router.post("/usage", response_model=BillingLedgerEntry, status_code=status.HTTP_201_CREATED)
async def apply_usage_charge(
    payload: UsageChargeRequest,
    tenant_id: str = Depends(MANAGE_BILLING),
    service: BillingService = Depends(get_billing_service),
) -> BillingLedgerEntry:
    if tenant_id != payload.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    return await service.apply_usage_charge(
        tenant_id=payload.tenant_id,
        subject_id=payload.subject_id,
        amount_minor=payload.amount_minor,
        currency=payload.currency,
        payload=payload.payload,
    )


class BillingStatusResponse(BaseModel):
    plan: str
    messages_used: int
    messages_limit: int
    conversations_used: int


@router.get("/status", response_model=BillingStatusResponse)
async def get_billing_status(
    tenant_id: str = Depends(MANAGE_BILLING),
    app_store: AppStore = Depends(get_app_store),
) -> BillingStatusResponse:
    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    messages_used = app_store.count_messages(tenant_uuid)
    conversations_used = len(app_store.list_conversations(tenant_uuid))

    limit_map = {
        "free": 100,
        "start": 1000,
        "pro": 10000,
        "enterprise": 999999,
    }
    limit = limit_map.get(tenant.plan.lower(), 1000)

    return BillingStatusResponse(
        plan=tenant.plan,
        messages_used=messages_used,
        messages_limit=limit,
        conversations_used=conversations_used,
    )
