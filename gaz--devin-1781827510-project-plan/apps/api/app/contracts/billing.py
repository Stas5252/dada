from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from typing import Protocol

from pydantic import BaseModel, Field

from app.contracts.types import JsonValue


class BillingOperation(StrEnum):
    CREATE_INVOICE = "create_invoice"
    RECORD_PAYMENT = "record_payment"
    APPLY_USAGE = "apply_usage"


class BillingStatus(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    DUPLICATE = "duplicate"
    FAILED = "failed"


class BillingIdempotencyKey(BaseModel):
    tenant_id: str = Field(min_length=1)
    operation: BillingOperation
    subject_id: str = Field(min_length=1)
    request_hash: str = Field(min_length=64, max_length=64)

    @property
    def storage_key(self) -> str:
        return ":".join((self.tenant_id, self.operation.value, self.subject_id, self.request_hash))

    @classmethod
    def from_payload(
        cls,
        *,
        tenant_id: str,
        operation: BillingOperation,
        subject_id: str,
        payload: dict[str, JsonValue],
    ) -> BillingIdempotencyKey:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return cls(
            tenant_id=tenant_id,
            operation=operation,
            subject_id=subject_id,
            request_hash=sha256(encoded).hexdigest(),
        )


class BillingLedgerEntry(BaseModel):
    tenant_id: str = Field(min_length=1)
    idempotency_key: BillingIdempotencyKey
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    status: BillingStatus


class BillingIdempotencyRepository(Protocol):
    async def find(self, *, key: BillingIdempotencyKey) -> BillingLedgerEntry | None: ...

    async def save(self, *, entry: BillingLedgerEntry) -> BillingLedgerEntry: ...


def mark_duplicate_if_replayed(
    *,
    existing: BillingLedgerEntry | None,
    requested: BillingLedgerEntry,
) -> BillingLedgerEntry:
    if existing is None:
        return requested
    if existing.tenant_id != requested.tenant_id:
        raise ValueError("existing ledger entry tenant_id does not match requested tenant_id")
    return requested.model_copy(update={"status": BillingStatus.DUPLICATE})
