import ipaddress
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from yookassa.domain.notification import WebhookNotificationFactory

from app.api.v1.dependencies import require_tenant_permission
from app.billing_limits import build_billing_usage_snapshot
from app.billing_service import BillingService
from app.contracts.billing import BillingLedgerEntry
from app.contracts.types import JsonValue
from app.rbac import Permission
from app.service_factory import get_billing_service
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/billing", tags=["billing"])
MANAGE_BILLING = require_tenant_permission(Permission.MANAGE_BILLING)
READ_BILLING = require_tenant_permission(Permission.READ_BILLING)


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
    messages_remaining: int
    billing_period_start: str
    limit_exceeded: bool
    conversations_used: int


@router.get("/status", response_model=BillingStatusResponse)
async def get_billing_status(
    tenant_id: str = Depends(READ_BILLING),
    app_store: AppStore = Depends(get_app_store),
) -> BillingStatusResponse:
    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    usage = build_billing_usage_snapshot(tenant, app_store)
    conversations_used = len(app_store.list_conversations(tenant_uuid))

    return BillingStatusResponse(
        plan=tenant.plan,
        messages_used=usage.messages_used,
        messages_limit=usage.messages_limit,
        messages_remaining=usage.messages_remaining,
        billing_period_start=usage.period_start.isoformat(),
        limit_exceeded=usage.limit_exceeded,
        conversations_used=conversations_used,
    )


class CheckoutRequest(BaseModel):
    plan: str = Field(min_length=1, max_length=40)
    return_url: str | None = Field(default=None)


class CheckoutResponse(BaseModel):
    payment_id: str
    confirmation_url: str
    status: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    tenant_id: str = Depends(MANAGE_BILLING),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> CheckoutResponse:
    plan_prices: dict[str, int] = {
        "start": 2990,
        "business": 7990,
        "pro": 19990,
        "enterprise": 49990,
    }

    price_minor = plan_prices.get(payload.plan.lower())
    if price_minor is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan")

    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if settings.yookassa_shop_id and settings.yookassa_secret_key:
        from yookassa import Configuration, Payment

        Configuration.account_id = settings.yookassa_shop_id
        Configuration.secret_key = settings.yookassa_secret_key

        return_url = payload.return_url or f"{settings.api_public_url}/billing?notice=payment-success"
        cancel_url = f"{settings.api_public_url}/billing?notice=payment-cancelled"

        payment = Payment.create(
            {
                "amount": {"value": f"{price_minor}.00", "currency": "RUB"},
                "capture": True,
                "description": f"CallForce подписка: {payload.plan}",
                "metadata": {
                    "tenant_id": tenant_id,
                    "plan_name": payload.plan.lower(),
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                },
            }
        )

        return CheckoutResponse(
            payment_id=payment.id,
            confirmation_url=payment.confirmation.confirmation_url,
            status=payment.status,
        )

    return CheckoutResponse(
        payment_id=f"local-{uuid4().hex[:12]}",
        confirmation_url=f"{settings.api_public_url}/billing/checkout?plan={payload.plan.lower()}",
        status="pending_local",
    )


logger = logging.getLogger(__name__)

YOOKASSA_IP_NETWORKS = [
    ipaddress.ip_network("185.71.76.0/22"),
    ipaddress.ip_network("77.75.153.0/25"),
    ipaddress.ip_network("77.75.153.128/25"),
    ipaddress.ip_network("77.75.154.0/25"),
    ipaddress.ip_network("77.75.154.128/25"),
    ipaddress.ip_network("77.75.156.0/23"),
]


def _is_yookassa_ip(ip_str: str | None) -> bool:
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return any(ip in network for network in YOOKASSA_IP_NETWORKS)
    except ValueError:
        return False


@router.post("/yookassa/webhook")
async def yookassa_webhook(
    request: Request,
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """
    Handle incoming YooKassa payment events.
    Verifies IP ranges and queries YooKassa API to verify authenticity.
    """
    # 1. IP Range Check (bypass for local/test environments)
    if settings.app_env not in ("local", "test", "development"):
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        client_ip = request.headers.get("x-real-ip") or forwarded_for or (request.client.host if request.client else None)
        if not _is_yookassa_ip(client_ip):
            logger.warning("Rejected YooKassa webhook request from untrusted IP: %s", client_ip)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Untrusted sender IP")

    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from e

    # 2. Parse using WebhookNotificationFactory
    try:
        notification = WebhookNotificationFactory().create(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook payload: {exc}") from exc

    event_type = notification.event
    if event_type == "payment.succeeded":
        payment_obj = notification.object
        payment_id = payment_obj.id
        
        # 3. Authenticity verification via API query
        if settings.yookassa_shop_id and settings.yookassa_secret_key:
            from yookassa import Configuration, Payment
            Configuration.account_id = settings.yookassa_shop_id
            Configuration.secret_key = settings.yookassa_secret_key
            try:
                payment = Payment.find_one(payment_id)
            except Exception as e:
                logger.error(f"Failed to verify payment {payment_id} with YooKassa API: {e}")
                # We return OK so YooKassa doesn't infinitely retry if API goes down temporarily
                return {"status": "ok"}

            if payment.status != "succeeded":
                logger.error(f"YooKassa Payment {payment_id} status is {payment.status}, expected succeeded")
                # Return 200 OK so YooKassa doesn't infinitely retry a non-succeeded payload
                return {"status": "ok"}
            payment_obj = payment

        metadata = getattr(payment_obj, "metadata", {}) or {}
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
