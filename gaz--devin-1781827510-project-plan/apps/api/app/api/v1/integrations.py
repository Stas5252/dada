from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.dependencies import require_tenant_permission
from app.channels import ChannelType, OutboundMessage
from app.channels.telegram_adapter import TelegramChannelAdapter
from app.contracts.integrations import (
    IikoMenuItem,
    IikoOrderDraft,
    IikoOrderResult,
    WebhookSignature,
)
from app.contracts.types import JsonValue
from app.integration_services import (
    LocalIikoAdapter,
    LocalYooKassaAdapter,
    TelegramOutboundMessage,
    TelegramSendResult,
    YooKassaPaymentDraft,
    YooKassaPaymentResult,
)
from app.rbac import Permission
from app.service_factory import (
    get_iiko_adapter,
    get_telegram_adapter,
    get_webhook_signer,
    get_yookassa_adapter,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])
READ_INTEGRATIONS = require_tenant_permission(Permission.READ_KNOWLEDGE)
MANAGE_INTEGRATIONS = require_tenant_permission(Permission.MANAGE_CHAT)


class WebhookSignRequest(BaseModel):
    body: dict[str, JsonValue]
    timestamp: int
    nonce: str


class WebhookVerifyRequest(BaseModel):
    body: dict[str, JsonValue]
    signature: WebhookSignature


@router.get("/iiko/menu", response_model=list[IikoMenuItem])
async def fetch_iiko_menu(
    tenant_id: str = Depends(READ_INTEGRATIONS),
    iiko: LocalIikoAdapter = Depends(get_iiko_adapter),
) -> list[IikoMenuItem]:
    return await iiko.fetch_menu(tenant_id=tenant_id)


@router.post("/iiko/orders", response_model=IikoOrderResult, status_code=status.HTTP_201_CREATED)
async def create_iiko_order(
    draft: IikoOrderDraft,
    dry_run: bool = True,
    tenant_id: str = Depends(MANAGE_INTEGRATIONS),
    iiko: LocalIikoAdapter = Depends(get_iiko_adapter),
) -> IikoOrderResult:
    _assert_tenant_matches(tenant_id, draft.tenant_id)
    return await iiko.create_order(draft=draft, dry_run=dry_run)


@router.post(
    "/telegram/messages",
    response_model=TelegramSendResult,
    status_code=status.HTTP_201_CREATED,
)
async def send_telegram_message(
    message: TelegramOutboundMessage,
    tenant_id: str = Depends(MANAGE_INTEGRATIONS),
    telegram: TelegramChannelAdapter = Depends(get_telegram_adapter),
) -> TelegramSendResult:
    _assert_tenant_matches(tenant_id, message.tenant_id)

    if telegram.dedup.is_duplicate(f"tg-out:{message.idempotency_key}"):
        return TelegramSendResult(
            tenant_id=message.tenant_id,
            chat_id=message.chat_id,
            external_message_id="dup",
            duplicate=True,
        )

    outbound = OutboundMessage(
        channel=ChannelType.telegram,
        external_chat_id=message.chat_id,
        text=message.text,
    )
    result = await telegram.send_message(outbound)

    return TelegramSendResult(
        tenant_id=message.tenant_id,
        chat_id=message.chat_id,
        external_message_id=result.external_message_id or "error",
        duplicate=False,
    )


@router.post(
    "/yookassa/payments",
    response_model=YooKassaPaymentResult,
    status_code=status.HTTP_201_CREATED,
)
async def create_yookassa_payment(
    draft: YooKassaPaymentDraft,
    tenant_id: str = Depends(MANAGE_INTEGRATIONS),
    yookassa: LocalYooKassaAdapter = Depends(get_yookassa_adapter),
) -> YooKassaPaymentResult:
    _assert_tenant_matches(tenant_id, draft.tenant_id)
    return await yookassa.create_payment(draft)


@router.post("/webhooks/sign", response_model=WebhookSignature)
async def sign_webhook(
    payload: WebhookSignRequest,
    tenant_id: str = Depends(MANAGE_INTEGRATIONS),
) -> WebhookSignature:
    signer = get_webhook_signer(tenant_id)
    return signer.sign(body=payload.body, timestamp=payload.timestamp, nonce=payload.nonce)


@router.post("/webhooks/verify", response_model=bool)
async def verify_webhook(
    payload: WebhookVerifyRequest,
    tenant_id: str = Depends(MANAGE_INTEGRATIONS),
) -> bool:
    signer = get_webhook_signer(tenant_id)
    return signer.verify(body=payload.body, signature=payload.signature)


def _assert_tenant_matches(header_tenant_id: str, payload_tenant_id: str) -> None:
    if header_tenant_id != payload_tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
