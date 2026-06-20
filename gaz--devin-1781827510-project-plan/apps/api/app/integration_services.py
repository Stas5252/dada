from dataclasses import dataclass, field
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field

from app.contracts.integrations import (
    IikoMenuItem,
    IikoOrderDraft,
    IikoOrderResult,
    IikoOrderStatus,
    WebhookSignature,
    WebhookSigningConfig,
    sign_custom_webhook,
    verify_custom_webhook_signature,
)
from app.contracts.types import JsonValue


class TelegramInboundMessage(BaseModel):
    tenant_id: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class TelegramOutboundMessage(BaseModel):
    tenant_id: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=4096)
    idempotency_key: str = Field(min_length=1)


class TelegramSendResult(BaseModel):
    tenant_id: str = Field(min_length=1)
    chat_id: str = Field(min_length=1)
    external_message_id: str = Field(min_length=1)
    duplicate: bool = False


class YooKassaPaymentDraft(BaseModel):
    tenant_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    description: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1)


class YooKassaPaymentResult(BaseModel):
    tenant_id: str = Field(min_length=1)
    payment_id: str = Field(min_length=1)
    confirmation_url: str = Field(min_length=1)
    status: str = "pending"
    duplicate: bool = False


@dataclass
class LocalIikoAdapter:
    menus: dict[str, list[IikoMenuItem]] = field(default_factory=dict)
    orders_by_idempotency_key: dict[str, IikoOrderResult] = field(default_factory=dict)

    async def fetch_menu(self, *, tenant_id: str) -> list[IikoMenuItem]:
        return list(self.menus.get(tenant_id, ()))

    async def create_order(self, *, draft: IikoOrderDraft, dry_run: bool) -> IikoOrderResult:
        existing_order = self.orders_by_idempotency_key.get(draft.idempotency_key)
        if existing_order is not None:
            return existing_order

        import httpx

        from app.settings import get_settings

        settings = get_settings()
        external_order_id = _stable_external_id("iiko-order", draft.idempotency_key)

        if settings.iiko_api_login and not dry_run:
            async with httpx.AsyncClient() as client:
                try:
                    # 1. Get access token
                    auth_res = await client.post(
                        "https://api-ru.iiko.services/api/1/access_token",
                        json={"apiLogin": settings.iiko_api_login},
                    )
                    auth_res.raise_for_status()
                    token = auth_res.json().get("token")

                    # 2. Create order
                    order_res = await client.post(
                        "https://api-ru.iiko.services/api/1/deliveries/create",
                        headers={"Authorization": f"Bearer {token}"},
                        json={
                            "organizationId": draft.tenant_id,  # Simplified for example
                            "order": {
                                "items": [
                                    {
                                        "amount": line.quantity,
                                        "productId": line.menu_item_external_id,
                                    }
                                    for line in draft.lines
                                ],
                                "phone": draft.customer_phone,
                            },
                        },
                    )
                    if order_res.status_code == 200:
                        data = order_res.json()
                        external_order_id = data.get("orderInfo", {}).get("id", external_order_id)
                except Exception as e:
                    print(f"iiko API error: {e}")

        order = IikoOrderResult(
            tenant_id=draft.tenant_id,
            external_order_id=external_order_id,
            status=IikoOrderStatus.ACCEPTED if not dry_run else IikoOrderStatus.COOKING,
            idempotency_key=draft.idempotency_key,
        )
        self.orders_by_idempotency_key[draft.idempotency_key] = order
        return order

    async def get_order_status(
        self,
        *,
        tenant_id: str,
        external_order_id: str,
    ) -> IikoOrderStatus:
        for order in self.orders_by_idempotency_key.values():
            if order.tenant_id == tenant_id and order.external_order_id == external_order_id:
                return order.status
        return IikoOrderStatus.CANCELLED


@dataclass
class LocalTelegramAdapter:
    sent_messages_by_idempotency_key: dict[str, TelegramSendResult] = field(default_factory=dict)

    async def send_message(self, message: TelegramOutboundMessage) -> TelegramSendResult:
        existing_message = self.sent_messages_by_idempotency_key.get(message.idempotency_key)
        if existing_message is not None:
            return existing_message.model_copy(update={"duplicate": True})

        import httpx

        from app.settings import get_settings

        settings = get_settings()
        external_message_id = _stable_external_id("telegram-message", message.idempotency_key)

        if settings.telegram_bot_token:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={"chat_id": message.chat_id, "text": message.text},
                )
                if res.status_code == 200:
                    data = res.json()
                    external_message_id = str(
                        data.get("result", {}).get("message_id", external_message_id)
                    )
                else:
                    print(f"Telegram API error: {res.status_code} {res.text}")

        result = TelegramSendResult(
            tenant_id=message.tenant_id,
            chat_id=message.chat_id,
            external_message_id=external_message_id,
        )
        self.sent_messages_by_idempotency_key[message.idempotency_key] = result
        return result


@dataclass
class LocalYooKassaAdapter:
    payments_by_idempotency_key: dict[str, YooKassaPaymentResult] = field(default_factory=dict)

    async def create_payment(self, draft: YooKassaPaymentDraft) -> YooKassaPaymentResult:
        existing_payment = self.payments_by_idempotency_key.get(draft.idempotency_key)
        if existing_payment is not None:
            return existing_payment.model_copy(update={"duplicate": True})

        from app.settings import get_settings

        settings = get_settings()
        if settings.yookassa_shop_id and settings.yookassa_secret_key:
            from yookassa import Configuration, Payment  # type: ignore[import-untyped]

            Configuration.account_id = settings.yookassa_shop_id
            Configuration.secret_key = settings.yookassa_secret_key

            res = Payment.create(
                {
                    "amount": {
                        "value": str(draft.amount_minor / 100.0),
                        "currency": draft.currency,
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": "https://your-domain.com/dashboard/billing",
                    },
                    "capture": True,
                    "description": draft.description,
                },
                draft.idempotency_key,
            )

            result = YooKassaPaymentResult(
                tenant_id=draft.tenant_id,
                payment_id=res.id,
                confirmation_url=res.confirmation.confirmation_url,
                status=res.status,
            )
            self.payments_by_idempotency_key[draft.idempotency_key] = result
            return result

        # Fallback to local stub
        payment_id = _stable_external_id("yookassa-payment", draft.idempotency_key)
        result = YooKassaPaymentResult(
            tenant_id=draft.tenant_id,
            payment_id=payment_id,
            confirmation_url=f"https://checkout.test.yookassa.local/{payment_id}",
        )
        self.payments_by_idempotency_key[draft.idempotency_key] = result
        return result


@dataclass(frozen=True)
class LocalWebhookSigner:
    config: WebhookSigningConfig
    signing_key: bytes

    def sign(self, *, body: dict[str, JsonValue], timestamp: int, nonce: str) -> WebhookSignature:
        return sign_custom_webhook(
            config=self.config,
            body=_canonical_body(body),
            timestamp=timestamp,
            nonce=nonce,
            signing_key=self.signing_key,
        )

    def verify(self, *, body: dict[str, JsonValue], signature: WebhookSignature) -> bool:
        return verify_custom_webhook_signature(
            config=self.config,
            body=_canonical_body(body),
            signing_key=self.signing_key,
            signature=signature,
        )


def _canonical_body(body: dict[str, JsonValue]) -> bytes:
    return str(sorted(body.items())).encode()


def _stable_external_id(prefix: str, idempotency_key: str) -> str:
    return f"{prefix}-{uuid5(NAMESPACE_URL, idempotency_key)}"
