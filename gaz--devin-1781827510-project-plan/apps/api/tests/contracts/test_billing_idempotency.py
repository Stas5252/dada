from __future__ import annotations

from app.contracts.billing import (
    BillingIdempotencyKey,
    BillingLedgerEntry,
    BillingOperation,
    BillingStatus,
    mark_duplicate_if_replayed,
)


def test_billing_idempotency_key_is_canonical_per_tenant_operation_and_subject() -> None:
    first = BillingIdempotencyKey.from_payload(
        tenant_id="tenant-a",
        operation=BillingOperation.CREATE_INVOICE,
        subject_id="invoice-1",
        payload={"amount_minor": 1200, "currency": "RUB"},
    )
    replay = BillingIdempotencyKey.from_payload(
        tenant_id="tenant-a",
        operation=BillingOperation.CREATE_INVOICE,
        subject_id="invoice-1",
        payload={"currency": "RUB", "amount_minor": 1200},
    )
    other_tenant = BillingIdempotencyKey.from_payload(
        tenant_id="tenant-b",
        operation=BillingOperation.CREATE_INVOICE,
        subject_id="invoice-1",
        payload={"amount_minor": 1200, "currency": "RUB"},
    )

    assert first == replay
    assert first.storage_key != other_tenant.storage_key
    assert first.storage_key.startswith("tenant-a:create_invoice:invoice-1:")


def test_billing_replay_is_marked_duplicate_without_mutating_original_entry() -> None:
    key = BillingIdempotencyKey.from_payload(
        tenant_id="tenant-a",
        operation=BillingOperation.RECORD_PAYMENT,
        subject_id="payment-1",
        payload={"amount_minor": 2000, "currency": "RUB"},
    )
    existing = BillingLedgerEntry(
        tenant_id="tenant-a",
        idempotency_key=key,
        amount_minor=2_000,
        currency="RUB",
        status=BillingStatus.APPLIED,
    )
    requested = existing.model_copy(update={"status": BillingStatus.PENDING})

    result = mark_duplicate_if_replayed(existing=existing, requested=requested)

    assert existing.status == BillingStatus.APPLIED
    assert result.status == BillingStatus.DUPLICATE
    assert result.tenant_id == "tenant-a"
