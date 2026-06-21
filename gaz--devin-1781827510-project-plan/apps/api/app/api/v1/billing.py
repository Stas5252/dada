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


from fastapi import Request
import logging
logger = logging.getLogger(__name__)

@router.post("/yookassa/webhook")
async def yookassa_webhook(
    request: Request,
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, str]:
    """
    Handle incoming YooKassa payment events.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("event")
    if event_type == "payment.succeeded":
        payment_obj = payload.get("object", {})
        metadata = payment_obj.get("metadata", {})
        
        tenant_id_str = metadata.get("tenant_id")
        new_plan = metadata.get("plan_name")
        
        if tenant_id_str and new_plan:
            try:
                tenant_uuid = UUID(tenant_id_str)
                tenant = app_store.get_tenant(tenant_uuid)
                if tenant:
                    app_store.update_tenant_plan(tenant_uuid, new_plan)
                    logger.info(f"Tenant {tenant_id_str} upgraded to {new_plan}")
            except Exception as e:
                logger.error(f"Failed to process payment metadata: {e}")

    return {"status": "ok"}
