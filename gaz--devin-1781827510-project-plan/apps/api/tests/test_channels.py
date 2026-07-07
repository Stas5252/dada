from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.channels import SendResult
from app.main import create_app
from app.schemas import AgentCreateRequest, RegisterRequest
from app.store_factory import get_app_store


def test_vk_webhook_confirmation() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=True)
    store = get_app_store()

    # Register tenant properly
    reg_payload = RegisterRequest(
        company_name="VK Confirm Tenant",
        owner_email=f"vk_confirm_{uuid4().hex}@example.com",
        owner_name="VK Owner",
        password="safe-password-123",
    )
    tenant, _, _ = store.register(reg_payload, "test-secret")
    tenant_id = tenant.id

    store.update_tenant_settings(
        tenant_id,
        {
            "vk_confirmation_code": "vk_confirm_12345",
            "vk_group_token": "vk_group_token_abc",
        },
    )

    # confirmation request
    payload = {"type": "confirmation", "group_id": 12345}

    response = client.post(f"/api/v1/webhooks/vk/{tenant_id}", json=payload)
    assert response.status_code == 200
    assert response.text == "vk_confirm_12345"


def test_vk_webhook_message_processing() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=True)
    store = get_app_store()

    reg_payload = RegisterRequest(
        company_name="VK Message Tenant",
        owner_email=f"vk_msg_{uuid4().hex}@example.com",
        owner_name="VK Owner",
        password="safe-password-123",
    )
    tenant, _, _ = store.register(reg_payload, "test-secret")
    tenant_id = tenant.id

    store.update_tenant_settings(
        tenant_id,
        {"vk_group_token": "vk_group_token_abc"},
    )

    # Create a published agent via create_agent + publish_agent
    agent = store.create_agent(
        tenant_id,
        AgentCreateRequest(
            name="VK Agent",
            prompt="Привет! Я бот поддержки VK.",
            channel="vk",
        ),
    )
    store.publish_agent(tenant_id, agent.id)

    payload = {
        "type": "message_new",
        "object": {
            "message": {
                "peer_id": 999888,
                "text": "Какое меню?",
                "conversation_message_id": 123,
            }
        },
    }

    with patch("app.channels.vk_adapter.VKChannelAdapter.send_message") as mock_send:
        mock_send.return_value = SendResult(success=True, external_message_id="vk_msg_1")
        response = client.post(f"/api/v1/webhooks/vk/{tenant_id}", json=payload)
        assert response.status_code == 200
        assert response.text == "ok"
        assert mock_send.called

        # Deduplication check
        mock_send.reset_mock()
        response_dup = client.post(f"/api/v1/webhooks/vk/{tenant_id}", json=payload)
        assert response_dup.status_code == 200
        assert response_dup.text == "ok"
        assert not mock_send.called


def test_whatsapp_webhook_verification() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=True)
    store = get_app_store()

    reg_payload = RegisterRequest(
        company_name="WA Verify Tenant",
        owner_email=f"wa_verify_{uuid4().hex}@example.com",
        owner_name="WA Owner",
        password="safe-password-123",
    )
    tenant, _, _ = store.register(reg_payload, "test-secret")
    tenant_id = tenant.id

    store.update_tenant_settings(
        tenant_id,
        {"whatsapp_verify_token": "my_wa_token_123"},
    )

    # Verify happy path
    response = client.get(
        f"/api/v1/webhooks/whatsapp/{tenant_id}",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "my_wa_token_123",
            "hub.challenge": "challenge_accepted",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge_accepted"

    # Verify mismatch path
    response_fail = client.get(
        f"/api/v1/webhooks/whatsapp/{tenant_id}",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "challenge_accepted",
        },
    )
    assert response_fail.status_code == 403


def test_whatsapp_webhook_message_processing() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=True)
    store = get_app_store()

    reg_payload = RegisterRequest(
        company_name="WA Msg Tenant",
        owner_email=f"wa_msg_{uuid4().hex}@example.com",
        owner_name="WA Owner",
        password="safe-password-123",
    )
    tenant, _, _ = store.register(reg_payload, "test-secret")
    tenant_id = tenant.id

    store.update_tenant_settings(
        tenant_id,
        {
            "whatsapp_token": "wa_token_secret",
            "whatsapp_phone_number_id": "wa_phone_id_1",
            "whatsapp_app_secret": "wa_secret",
        },
    )

    # Create published agent
    agent = store.create_agent(
        tenant_id,
        AgentCreateRequest(
            name="WA Agent",
            prompt="Привет! Я бот поддержки WhatsApp.",
            channel="whatsapp",
        ),
    )
    store.publish_agent(tenant_id, agent.id)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "wa_msg_id_101",
                                    "from": "79998887766",
                                    "type": "text",
                                    "text": {"body": "Где пицца?"},
                                }
                            ],
                            "contacts": [
                                {
                                    "wa_id": "79998887766",
                                    "profile": {"name": "Alex WA"},
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }

    import hashlib
    import hmac
    import json
    body_bytes = json.dumps(payload).encode("utf-8")
    expected_sig = "sha256=" + hmac.new(b"wa_secret", body_bytes, hashlib.sha256).hexdigest()

    with patch("app.channels.whatsapp_adapter.WhatsAppChannelAdapter.send_message") as mock_send:
        mock_send.return_value = SendResult(success=True, external_message_id="wa_msg_resp_1")
        response = client.post(
            f"/api/v1/webhooks/whatsapp/{tenant_id}", 
            content=body_bytes,
            headers={"x-hub-signature-256": expected_sig, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert mock_send.called

        # Deduplication check
        mock_send.reset_mock()
        response_dup = client.post(
            f"/api/v1/webhooks/whatsapp/{tenant_id}", 
            content=body_bytes,
            headers={"x-hub-signature-256": expected_sig, "Content-Type": "application/json"}
        )
        assert response_dup.status_code == 200
        assert not mock_send.called
