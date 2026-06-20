from __future__ import annotations

from collections.abc import Mapping

from app.contracts.types import JsonValue

MASKED_VALUE = "<masked>"
CROSS_TENANT_VALUE = "<cross-tenant-redacted>"
SENSITIVE_FIELD_NAMES = frozenset(
    {
        "access_token",
        "address",
        "api_key",
        "card_pan",
        "customer_name",
        "email",
        "name",
        "password",
        "phone",
        "secret",
        "token",
    }
)


class TenantBoundaryError(ValueError):
    """Raised when a payload is explicitly scoped to another tenant."""


def assert_same_tenant(*, expected_tenant_id: str, actual_tenant_id: str) -> None:
    if actual_tenant_id != expected_tenant_id:
        raise TenantBoundaryError("payload tenant_id does not match context tenant_id")


def mask_tenant_payload(
    payload: Mapping[str, JsonValue],
    *,
    tenant_id: str,
) -> dict[str, JsonValue]:
    payload_tenant_id = payload.get("tenant_id")
    if isinstance(payload_tenant_id, str) and payload_tenant_id != tenant_id:
        return {"tenant_id": CROSS_TENANT_VALUE, "redacted": True}

    masked: dict[str, JsonValue] = {}
    for key, value in payload.items():
        masked[key] = _mask_value(key=key, value=value, tenant_id=tenant_id)
    return masked


def _mask_value(*, key: str, value: JsonValue, tenant_id: str) -> JsonValue:
    if key.lower() in SENSITIVE_FIELD_NAMES:
        return MASKED_VALUE
    if isinstance(value, dict):
        return mask_tenant_payload(value, tenant_id=tenant_id)
    if isinstance(value, list):
        return [_mask_value(key="", value=item, tenant_id=tenant_id) for item in value]
    return value
