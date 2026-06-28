from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

SCHEMA_DIR = Path(__file__).resolve().parents[4] / "docs" / "api" / "schemas"


def load_schema(filename: str) -> dict[str, Any]:
    path = SCHEMA_DIR / filename
    return json.loads(path.read_text())


@pytest.mark.parametrize(
    "schema_file",
    [
        "action-tool-contract.schema.json",
        "billing-idempotency-key.schema.json",
        "custom-webhook-signature.schema.json",
        "voice-session.schema.json",
    ],
)
def test_schema_examples_are_valid(schema_file: str) -> None:
    schema = load_schema(schema_file)
    examples = schema.get("examples", [])
    assert examples, f"Schema {schema_file} has no examples"
    
    for example in examples:
        # Validate that each example in the schema itself conforms to the schema rules
        jsonschema.validate(instance=example, schema=schema)


def test_action_tool_contract_validation() -> None:
    schema = load_schema("action-tool-contract.schema.json")
    
    # Valid instance
    valid_instance = {
        "name": "test_tool",
        "version": "1.0.0",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "permissions": ["read:menu"],
        "timeout_ms": 3000,
        "destructive": False,
        "requires_confirmation": False,
        "idempotency": {
            "required": True,
            "scope": "tenant",
            "key_fields": ["tenant_id"],
        },
        "retry_policy": {
            "max_attempts": 2,
            "backoff_ms": 100,
            "only_when_idempotent": True,
        },
        "audit_enabled": True,
    }
    jsonschema.validate(instance=valid_instance, schema=schema)
    
    # Invalid permission name
    invalid_permission = valid_instance.copy()
    invalid_permission["permissions"] = ["invalid:permission"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_permission, schema=schema)

    # Missing required field
    missing_field = valid_instance.copy()
    del missing_field["name"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=missing_field, schema=schema)


def test_voice_session_contract_validation() -> None:
    schema = load_schema("voice-session.schema.json")
    
    # Valid instance
    valid_instance = {
        "tenant_id": "tenant-123",
        "session_id": "session-456",
        "state": "thinking",
        "pending_confirmation_id": None,
        "transcript": [
            {"speaker": "customer", "text": "hello"},
            {"speaker": "assistant", "text": "how can I help you?"},
        ],
    }
    jsonschema.validate(instance=valid_instance, schema=schema)

    # Invalid state enum
    invalid_state = valid_instance.copy()
    invalid_state["state"] = "invalid_state"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_state, schema=schema)
