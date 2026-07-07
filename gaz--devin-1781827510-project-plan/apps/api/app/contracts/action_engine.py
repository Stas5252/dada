from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.masking import mask_tenant_payload
from app.contracts.types import JsonValue


class ToolPermission(StrEnum):
    READ_MENU = "read:menu"
    CREATE_ORDER = "create:order"
    CANCEL_ORDER = "cancel:order"
    SEND_WEBHOOK = "send:webhook"
    MANAGE_BILLING = "manage:billing"
    MANAGE_CRM = "manage:crm"
    MANAGE_APPOINTMENTS = "manage:appointments"


class ConfirmationError(ValueError):
    """Raised when a tool invocation is missing a matching confirmation."""


class IdempotencyError(ValueError):
    """Raised when an invocation is missing a required idempotency key."""


class ContractMismatchError(ValueError):
    """Raised when an invocation does not target the provided tool contract."""


class IdempotencyPolicy(BaseModel):
    required: bool = True
    scope: Literal["tenant", "tenant_tool", "tenant_tool_subject"] = "tenant_tool_subject"
    key_fields: tuple[str, ...] = ("tenant_id", "tool_name", "subject_id")


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=1, ge=1, le=5)
    backoff_ms: int = Field(default=0, ge=0, le=60_000)
    only_when_idempotent: bool = True


class ToolContract(BaseModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    input_schema: dict[str, JsonValue]
    output_schema: dict[str, JsonValue]
    permissions: frozenset[ToolPermission]
    timeout_ms: int = Field(gt=0, le=30_000)
    destructive: bool = False
    requires_confirmation: bool = False
    idempotency: IdempotencyPolicy = Field(default_factory=IdempotencyPolicy)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    audit_enabled: bool = True


class ToolConfirmation(BaseModel):
    tenant_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    confirmed_by_subject_id: str = Field(min_length=1)
    confirmed_at: datetime


class ToolInvocation(BaseModel):
    tenant_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    input_payload: dict[str, JsonValue]
    idempotency_key: str | None = None
    confirmation: ToolConfirmation | None = None


class ToolAuditEvent(BaseModel):
    tenant_id: str
    tool_name: str
    idempotency_key: str | None
    masked_input_payload: dict[str, JsonValue]
    permissions: frozenset[ToolPermission]


def assert_tool_invocation_allowed(contract: ToolContract, invocation: ToolInvocation) -> None:
    if contract.name != invocation.tool_name:
        raise ContractMismatchError("invocation tool_name does not match contract name")
    if contract.idempotency.required and invocation.idempotency_key is None:
        raise IdempotencyError("idempotency_key is required by this tool contract")
    if contract.destructive or contract.requires_confirmation:
        _assert_confirmation_matches(invocation)


def build_tool_audit_event(contract: ToolContract, invocation: ToolInvocation) -> ToolAuditEvent:
    return ToolAuditEvent(
        tenant_id=invocation.tenant_id,
        tool_name=invocation.tool_name,
        idempotency_key=invocation.idempotency_key,
        masked_input_payload=mask_tenant_payload(
            invocation.input_payload,
            tenant_id=invocation.tenant_id,
        ),
        permissions=contract.permissions,
    )


def _assert_confirmation_matches(invocation: ToolInvocation) -> None:
    confirmation = invocation.confirmation
    if confirmation is None:
        raise ConfirmationError("destructive tool invocation requires confirmation")
    if confirmation.tenant_id != invocation.tenant_id:
        raise ConfirmationError("confirmation tenant_id does not match invocation tenant_id")
    if confirmation.tool_name != invocation.tool_name:
        raise ConfirmationError("confirmation tool_name does not match invocation tool_name")
    if confirmation.idempotency_key != invocation.idempotency_key:
        raise ConfirmationError("confirmation idempotency_key does not match invocation")
