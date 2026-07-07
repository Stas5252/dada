from uuid import UUID

from fastapi.testclient import TestClient

from app.billing_limits import BILLING_MONTHLY_MESSAGE_LIMIT_SETTING
from app.main import create_app
from app.store_factory import get_app_store


def test_billing_status_reports_remaining_and_custom_limit() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    store = get_app_store()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Limit Status Tenant",
            "owner_email": "limit-status@example.com",
            "owner_name": "Limit Owner",
            "password": "safe-local-password",
        },
    )
    assert register_response.status_code == 201
    tenant_id = UUID(register_response.json()["tenant"]["id"])
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "x-tenant-id": str(tenant_id)}

    store.update_tenant_settings(tenant_id, {BILLING_MONTHLY_MESSAGE_LIMIT_SETTING: 0})

    response = client.get("/api/v1/billing/status", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["messages_used"] == 0
    assert payload["messages_limit"] == 0
    assert payload["messages_remaining"] == 0
    assert payload["limit_exceeded"] is True
    assert payload["billing_period_start"]


def test_billing_limit_blocks_mock_chat_before_message_creation_and_audits() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    store = get_app_store()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Limit Block Tenant",
            "owner_email": "limit-block@example.com",
            "owner_name": "Limit Owner",
            "password": "safe-local-password",
        },
    )
    assert register_response.status_code == 201
    tenant_id = UUID(register_response.json()["tenant"]["id"])
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "x-tenant-id": str(tenant_id)}

    store.update_tenant_settings(tenant_id, {BILLING_MONTHLY_MESSAGE_LIMIT_SETTING: 0})
    agent_response = client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "name": "Limit Agent",
            "prompt": "Answer briefly and politely.",
            "channel": "web_widget",
        },
    )
    assert agent_response.status_code == 201

    response = client.post(
        "/api/v1/chat/mock",
        headers=headers,
        json={
            "agent_id": agent_response.json()["id"],
            "channel": "web_widget",
            "message": "Hello",
        },
    )

    assert response.status_code == 402
    payload = response.json()["detail"]
    assert payload["error_code"] == "BILLING_LIMIT_REACHED"
    assert payload["messages_limit"] == 0
    assert payload["messages_remaining"] == 0
    assert store.list_conversations(tenant_id) == []
    assert any(
        event.event_type == "billing.limit_blocked"
        and event.details["source"] == "chat_mock"
        and event.details["messages_limit"] == "0"
        for event in store.list_audit_logs(tenant_id)
    )
