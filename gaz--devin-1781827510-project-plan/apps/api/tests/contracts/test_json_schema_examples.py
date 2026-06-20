from __future__ import annotations

import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parents[4] / "docs" / "api" / "schemas"


def test_json_schema_examples_are_valid_json_objects() -> None:
    schema_paths = sorted(SCHEMA_DIR.glob("*.schema.json"))

    assert {path.name for path in schema_paths} == {
        "action-tool-contract.schema.json",
        "billing-idempotency-key.schema.json",
        "custom-webhook-signature.schema.json",
        "voice-session.schema.json",
    }

    for path in schema_paths:
        payload = json.loads(path.read_text())
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["type"] == "object"
        assert payload["examples"]
