from __future__ import annotations

import hmac
from collections.abc import Sequence
from enum import StrEnum
from hashlib import sha256
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.contracts.types import JsonValue


class IikoOrderStatus(StrEnum):
    ACCEPTED = "accepted"
    COOKING = "cooking"
    READY = "ready"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class IikoMenuItem(BaseModel):
    tenant_id: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price_minor: int = Field(ge=0)
    available: bool
    modifiers_schema: dict[str, JsonValue] = Field(default_factory=dict)


class IikoOrderLine(BaseModel):
    menu_item_external_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    modifiers: dict[str, JsonValue] = Field(default_factory=dict)


class IikoOrderDraft(BaseModel):
    tenant_id: str = Field(min_length=1)
    customer_phone: str = Field(min_length=1)
    delivery_address: str = Field(min_length=1)
    lines: list[IikoOrderLine] = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class IikoOrderResult(BaseModel):
    tenant_id: str = Field(min_length=1)
    external_order_id: str = Field(min_length=1)
    status: IikoOrderStatus
    idempotency_key: str = Field(min_length=1)


class IikoAdapter(Protocol):
    async def fetch_menu(self, *, tenant_id: str) -> Sequence[IikoMenuItem]: ...

    async def create_order(self, *, draft: IikoOrderDraft, dry_run: bool) -> IikoOrderResult: ...

    async def get_order_status(
        self,
        *,
        tenant_id: str,
        external_order_id: str,
    ) -> IikoOrderStatus: ...


class WebhookSigningConfig(BaseModel):
    tenant_id: str = Field(min_length=1)
    key_id: str = Field(min_length=1)
    algorithm: Literal["HMAC-SHA256"] = "HMAC-SHA256"


class WebhookSignature(BaseModel):
    key_id: str
    timestamp: int
    nonce: str
    signature: str
    algorithm: Literal["HMAC-SHA256"] = "HMAC-SHA256"


def sign_custom_webhook(
    *,
    config: WebhookSigningConfig,
    body: bytes,
    timestamp: int,
    nonce: str,
    signing_key: bytes,
) -> WebhookSignature:
    payload = _signature_payload(timestamp=timestamp, nonce=nonce, body=body)
    digest = hmac.new(signing_key, payload, sha256).hexdigest()
    return WebhookSignature(
        key_id=config.key_id,
        timestamp=timestamp,
        nonce=nonce,
        signature=digest,
    )


def verify_custom_webhook_signature(
    *,
    config: WebhookSigningConfig,
    body: bytes,
    signing_key: bytes,
    signature: WebhookSignature,
) -> bool:
    if signature.key_id != config.key_id or signature.algorithm != config.algorithm:
        return False
    expected = sign_custom_webhook(
        config=config,
        body=body,
        timestamp=signature.timestamp,
        nonce=signature.nonce,
        signing_key=signing_key,
    )
    return hmac.compare_digest(expected.signature, signature.signature)


def _signature_payload(*, timestamp: int, nonce: str, body: bytes) -> bytes:
    return b".".join((str(timestamp).encode(), nonce.encode(), body))
