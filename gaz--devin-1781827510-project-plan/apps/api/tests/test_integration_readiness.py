from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register_owner(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Readiness Tenant",
            "owner_email": f"readiness_{uuid4().hex}@example.com",
            "owner_name": "Readiness Owner",
            "password": "safe-password-123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    return data["access_token"], data["tenant"]["id"]


def _items_by_key(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    items = payload["items"]
    assert isinstance(items, list)
    return {str(item["key"]): item for item in items if isinstance(item, dict)}


def test_integration_readiness_reports_local_stubs_without_secret_values() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    token, tenant_id = _register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        f"/api/v1/tenants/{tenant_id}/settings/integration-readiness",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "action_required"
    items = _items_by_key(payload)
    assert items["web_widget"]["status"] == "configured"
    assert items["llm"]["status"] == "local_stub"
    assert items["llm"]["blocking"] is True
    assert "OPENAI_API_KEY" in items["llm"]["missing_settings"]
    assert "safe-password-123" not in response.text


def test_integration_readiness_uses_tenant_channel_settings() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    token, tenant_id = _register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}

    settings_response = client.post(
        f"/api/v1/tenants/{tenant_id}/settings",
        headers=headers,
        json={
            "settings": {
                "openai_api_key": "sk-test",
                "telegram_bot_token": "123456789:token",
                "yookassa_shop_id": "123456",
                "yookassa_secret_key": "test_secret",
            }
        },
    )
    assert settings_response.status_code == 200

    response = client.get(
        f"/api/v1/tenants/{tenant_id}/settings/integration-readiness",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    items = _items_by_key(payload)
    assert payload["status"] == "mock_mode"
    assert items["llm"]["status"] == "configured"
    assert items["telegram"]["status"] == "configured"
    assert items["yookassa"]["status"] == "configured"
    assert items["whatsapp"]["status"] == "needs_setup"
    assert "sk-test" not in response.text
    assert "test_secret" not in response.text
