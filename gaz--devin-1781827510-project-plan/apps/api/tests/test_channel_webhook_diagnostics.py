from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register_owner(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Webhook Diagnostics Tenant",
            "owner_email": f"webhook_diag_{uuid4().hex}@example.com",
            "owner_name": "Webhook Owner",
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


def test_channel_webhook_diagnostics_reports_urls_without_secret_values() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    token, tenant_id = _register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}

    settings_response = client.post(
        f"/api/v1/tenants/{tenant_id}/settings",
        headers=headers,
        json={
            "settings": {
                "vk_group_token": "vk-secret-token",
                "vk_confirmation_code": "vk-confirm",
                "vk_secret_key": "vk-callback-secret",
                "whatsapp_token": "wa-secret-token",
                "whatsapp_phone_number_id": "1234567890",
                "whatsapp_verify_token": "wa-verify-secret",
                "whatsapp_app_secret": "wa-app-secret",
            }
        },
    )
    assert settings_response.status_code == 200

    response = client.get(
        f"/api/v1/tenants/{tenant_id}/settings/channel-webhooks",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["public_url_status"] == "local_only"
    items = _items_by_key(payload)
    assert items["vk"]["inbound_webhook_url"].endswith(f"/api/v1/webhooks/vk/{tenant_id}")
    assert items["whatsapp"]["inbound_webhook_url"].endswith(
        f"/api/v1/webhooks/whatsapp/{tenant_id}"
    )
    assert "API_PUBLIC_URL_HTTPS" in items["vk"]["missing_settings"]
    assert "API_PUBLIC_URL_HTTPS" in items["whatsapp"]["missing_settings"]
    assert "vk-secret-token" not in response.text
    assert "vk-confirm" not in response.text
    assert "vk-callback-secret" not in response.text
    assert "wa-secret-token" not in response.text
    assert "wa-verify-secret" not in response.text
    assert "wa-app-secret" not in response.text


def test_channel_webhook_diagnostics_flags_whatsapp_app_secret_gap() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    token, tenant_id = _register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}

    settings_response = client.post(
        f"/api/v1/tenants/{tenant_id}/settings",
        headers=headers,
        json={
            "settings": {
                "whatsapp_token": "wa-token",
                "whatsapp_phone_number_id": "1234567890",
                "whatsapp_verify_token": "wa-verify",
            }
        },
    )
    assert settings_response.status_code == 200

    response = client.get(
        f"/api/v1/tenants/{tenant_id}/settings/channel-webhooks",
        headers=headers,
    )

    assert response.status_code == 200
    items = _items_by_key(response.json())
    assert items["whatsapp"]["status"] == "needs_setup"
    assert "whatsapp_app_secret" in items["whatsapp"]["missing_settings"]
