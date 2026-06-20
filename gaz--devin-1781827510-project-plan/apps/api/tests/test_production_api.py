from fastapi.testclient import TestClient

from app.main import create_app
from app.service_factory import (
    get_billing_service,
    get_iiko_adapter,
    get_telegram_adapter,
    get_voice_service,
    get_yookassa_adapter,
)


def test_production_service_api_endpoints_are_idempotent() -> None:
    _clear_service_caches()
    app = create_app()
    client = TestClient(app)

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Prod Tenant",
            "owner_email": "prod@example.com",
            "owner_name": "Prod Owner",
            "password": "safe-local-password",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant"]["id"]
    token = register_response.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}", "x-tenant-id": tenant_id}

    order_payload = {
        "tenant_id": tenant_id,
        "customer_phone": "+79990000000",
        "delivery_address": "Moscow",
        "lines": [{"menu_item_external_id": "pizza-1", "quantity": 1}],
        "idempotency_key": "order-1",
    }
    order = client.post(
        "/api/v1/integrations/iiko/orders",
        headers=headers,
        json=order_payload,
    )
    replayed_order = client.post(
        "/api/v1/integrations/iiko/orders",
        headers=headers,
        json=order_payload,
    )
    assert order.status_code == 201
    assert replayed_order.json() == order.json()

    telegram_payload = {
        "tenant_id": tenant_id,
        "chat_id": "chat-1",
        "text": "Hello",
        "idempotency_key": "telegram-1",
    }
    telegram = client.post(
        "/api/v1/integrations/telegram/messages",
        headers=headers,
        json=telegram_payload,
    )
    replayed_telegram = client.post(
        "/api/v1/integrations/telegram/messages",
        headers=headers,
        json=telegram_payload,
    )
    assert telegram.status_code == 201
    assert replayed_telegram.json()["duplicate"] is True

    payment_payload = {
        "tenant_id": tenant_id,
        "subject_id": "invoice-1",
        "amount_minor": 10000,
        "currency": "RUB",
        "description": "Invoice",
        "idempotency_key": "payment-1",
    }
    payment = client.post(
        "/api/v1/integrations/yookassa/payments",
        headers=headers,
        json=payment_payload,
    )
    replayed_payment = client.post(
        "/api/v1/integrations/yookassa/payments",
        headers=headers,
        json=payment_payload,
    )
    assert payment.status_code == 201
    assert replayed_payment.json()["payment_id"] == payment.json()["payment_id"]
    assert replayed_payment.json()["duplicate"] is True

    usage_payload = {
        "tenant_id": tenant_id,
        "subject_id": "call-1",
        "amount_minor": 2500,
        "currency": "RUB",
        "payload": {"minutes": 1},
    }
    usage = client.post("/api/v1/billing/usage", headers=headers, json=usage_payload)
    replayed_usage = client.post("/api/v1/billing/usage", headers=headers, json=usage_payload)
    assert usage.status_code == 201
    assert usage.json()["status"] == "applied"
    assert replayed_usage.json()["status"] == "duplicate"


def test_voice_and_webhook_api_endpoints() -> None:
    _clear_service_caches()
    app = create_app()
    client = TestClient(app)
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Prod Tenant 2",
            "owner_email": "prod2@example.com",
            "owner_name": "Prod Owner 2",
            "password": "safe-local-password",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant"]["id"]
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "x-tenant-id": tenant_id}

    started_session = client.post("/api/v1/voice/sessions", headers=headers)
    assert started_session.status_code == 201
    session_id = started_session.json()["session_id"]
    event_response = client.post(
        f"/api/v1/voice/sessions/{session_id}/events",
        headers=headers,
        json={
            "tenant_id": tenant_id,
            "event": "user_utterance",
            "turn": {"speaker": "customer", "text": "Hi"},
        },
    )
    assert event_response.status_code == 200
    assert event_response.json()["state"] == "thinking"

    signature_response = client.post(
        "/api/v1/integrations/webhooks/sign",
        headers=headers,
        json={"body": {"event": "order.created"}, "timestamp": 1, "nonce": "n"},
    )
    verify_response = client.post(
        "/api/v1/integrations/webhooks/verify",
        headers=headers,
        json={
            "body": {"event": "order.created"},
            "signature": signature_response.json(),
        },
    )
    assert verify_response.json() is True


def test_voice_preview_turn_persists_session_and_conversation_log() -> None:
    _clear_service_caches()
    app = create_app()
    client = TestClient(app)
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Voice Tenant",
            "owner_email": "voice@example.com",
            "owner_name": "Voice Owner",
            "password": "safe-local-password",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant"]["id"]
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "x-tenant-id": tenant_id}

    agent_response = client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "name": "Voice Preview Agent",
            "prompt": "Answer restaurant questions using the knowledge base.",
            "channel": "sip",
        },
    )
    assert agent_response.status_code == 201
    agent_id = agent_response.json()["id"]

    preview_response = client.post(
        "/api/v1/voice/sessions/preview-session-1/preview-turn",
        headers=headers,
        json={"agent_id": agent_id, "text": "Сколько стоит доставка?"},
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["session"]["state"] == "listening"
    assert preview_payload["session"]["transcript"][0] == {
        "speaker": "customer",
        "text": "Сколько стоит доставка?",
    }
    assert preview_payload["session"]["transcript"][1]["speaker"] == "assistant"
    assert preview_payload["conversation_id"]

    session_response = client.get(
        "/api/v1/voice/sessions/preview-session-1",
        headers=headers,
    )
    assert session_response.status_code == 200
    assert len(session_response.json()["transcript"]) == 2

    conversation_response = client.get(
        f"/api/v1/conversations/{preview_payload['conversation_id']}",
        headers=headers,
    )
    assert conversation_response.status_code == 200
    messages = conversation_response.json()["messages"]
    assert [message["role"] for message in messages] == ["customer", "agent"]
    assert messages[0]["content"] == "Сколько стоит доставка?"


def _clear_service_caches() -> None:
    get_iiko_adapter.cache_clear()
    get_telegram_adapter.cache_clear()
    get_yookassa_adapter.cache_clear()
    get_voice_service.cache_clear()
    get_billing_service.cache_clear()
