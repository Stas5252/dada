from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.contracts.action_engine import (
    ConfirmationError,
    IdempotencyError,
    ToolConfirmation,
    ToolContract,
    ToolInvocation,
    ToolPermission,
    assert_tool_invocation_allowed,
    build_tool_audit_event,
)
from app.contracts.masking import CROSS_TENANT_VALUE, MASKED_VALUE


def _create_order_contract() -> ToolContract:
    return ToolContract(
        name="iiko.create_order",
        version="2026-06-19",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        permissions=frozenset({ToolPermission.CREATE_ORDER}),
        timeout_ms=5_000,
        destructive=True,
        requires_confirmation=True,
    )


def test_destructive_tool_requires_matching_confirmation() -> None:
    contract = _create_order_contract()
    invocation = ToolInvocation(
        tenant_id="tenant-a",
        tool_name="iiko.create_order",
        input_payload={"tenant_id": "tenant-a", "subject_id": "order-1"},
        idempotency_key="tenant-a:iiko.create_order:order-1",
    )

    with pytest.raises(ConfirmationError):
        assert_tool_invocation_allowed(contract, invocation)

    confirmed = invocation.model_copy(
        update={
            "confirmation": ToolConfirmation(
                tenant_id="tenant-a",
                tool_name="iiko.create_order",
                idempotency_key="tenant-a:iiko.create_order:order-1",
                confirmed_by_subject_id="customer-1",
                confirmed_at=datetime.now(UTC),
            )
        }
    )

    assert_tool_invocation_allowed(contract, confirmed)


def test_tool_contract_requires_idempotency_key() -> None:
    contract = _create_order_contract()
    invocation = ToolInvocation(
        tenant_id="tenant-a",
        tool_name="iiko.create_order",
        input_payload={"tenant_id": "tenant-a", "subject_id": "order-1"},
        confirmation=ToolConfirmation(
            tenant_id="tenant-a",
            tool_name="iiko.create_order",
            idempotency_key="tenant-a:iiko.create_order:order-1",
            confirmed_by_subject_id="customer-1",
            confirmed_at=datetime.now(UTC),
        ),
    )

    with pytest.raises(IdempotencyError):
        assert_tool_invocation_allowed(contract, invocation)


def test_tool_audit_event_masks_pii_without_cross_tenant_leaks() -> None:
    contract = _create_order_contract()
    invocation = ToolInvocation(
        tenant_id="tenant-a",
        tool_name="iiko.create_order",
        input_payload={
            "tenant_id": "tenant-a",
            "customer_name": "Audrey",
            "phone": "+15551234567",
            "nested": {"tenant_id": "tenant-b", "phone": "+15557654321", "order_id": "b-1"},
        },
        idempotency_key="tenant-a:iiko.create_order:order-1",
    )

    event = build_tool_audit_event(contract, invocation)

    assert event.tenant_id == "tenant-a"
    assert event.masked_input_payload["tenant_id"] == "tenant-a"
    assert event.masked_input_payload["customer_name"] == MASKED_VALUE
    assert event.masked_input_payload["phone"] == MASKED_VALUE
    assert event.masked_input_payload["nested"] == {
        "tenant_id": CROSS_TENANT_VALUE,
        "redacted": True,
    }
