from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.channel_policy import CHANNEL_POLICIES_SETTINGS_KEY
from app.main import create_app
from app.schemas import (
    AgentCreateRequest,
    ChannelCompliancePolicySettings,
    ChannelPoliciesSettings,
)
from app.store import InMemoryStore
from app.store_factory import get_app_store


def _register_owner(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "DNC Tenant",
            "owner_email": f"dnc_{uuid4().hex}@example.com",
            "owner_name": "DNC Owner",
            "password": "safe-password-123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    return data["access_token"], data["tenant"]["id"]


def test_contact_suppression_normalizes_phone_across_channels() -> None:
    store = InMemoryStore()
    tenant_id = uuid4()

    suppression = store.record_contact_suppression(
        tenant_id,
        "sms",
        "phone",
        "+7 (999) 000-00-00",
        reason="opt_out_requested",
        source="test",
    )

    assert suppression.channel == "*"
    assert suppression.value == "+79990000000"
    assert store.find_contact_suppression(tenant_id, "voice", phone="79990000000") == suppression
    assert store.find_contact_suppression(tenant_id, "whatsapp", external_id="79990000000") == suppression


def test_contact_consent_normalizes_phone_and_excludes_expired_records() -> None:
    store = InMemoryStore()
    tenant_id = uuid4()

    expired = store.record_contact_consent(
        tenant_id,
        "voice",
        "phone",
        "+7 (999) 222-33-44",
        source="test",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    assert expired.channel == "*"
    assert expired.value == "+79992223344"
    assert store.find_contact_consent(tenant_id, "voice", phone="+79992223344") is None

    consent = store.record_contact_consent(
        tenant_id,
        "whatsapp",
        "phone",
        "+7 (999) 222-33-44",
        source="test",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    assert consent.channel == "*"
    assert store.find_contact_consent(tenant_id, "voice", phone="79992223344") == consent


def test_contact_suppression_api_create_list_revoke() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    token, _tenant_id = _register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/v1/contact-suppressions",
        headers=headers,
        json={
            "channel": "sms",
            "contact_type": "phone",
            "value": "+7 999 111-22-33",
            "reason": "manual_test",
            "source": "qa",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["channel"] == "*"
    assert created["value"] == "+79991112233"
    assert created["status"] == "active"

    list_response = client.get("/api/v1/contact-suppressions", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]

    revoke_response = client.delete(
        f"/api/v1/contact-suppressions/{created['id']}",
        headers=headers,
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"


def test_contact_consent_api_create_list_revoke() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    token, _tenant_id = _register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/v1/contact-consents",
        headers=headers,
        json={
            "channel": "sms",
            "contact_type": "phone",
            "value": "+7 999 222-33-44",
            "consent_type": "Outbound_Contact",
            "source": "qa",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["channel"] == "*"
    assert created["value"] == "+79992223344"
    assert created["consent_type"] == "outbound_contact"
    assert created["status"] == "active"

    list_response = client.get("/api/v1/contact-consents", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]

    revoke_response = client.delete(
        f"/api/v1/contact-consents/{created['id']}",
        headers=headers,
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"


def test_operator_message_requires_contact_consent_when_policy_enabled() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    token, tenant_id = _register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}

    store = get_app_store()
    tenant_uuid = UUID(tenant_id)
    store.update_tenant_settings(
        tenant_uuid,
        {
            CHANNEL_POLICIES_SETTINGS_KEY: ChannelPoliciesSettings(
                web_widget=ChannelCompliancePolicySettings(
                    require_contact_consent_for_outbound=True,
                )
            ).model_dump(mode="json")
        },
    )
    agent = store.create_agent(
        tenant_uuid,
        AgentCreateRequest(
            name="Consent operator agent",
            prompt="Answer only after verifying outbound contact consent.",
            channel="web_widget",
        ),
    )
    customer = store.create_customer(
        tenant_uuid,
        "web_widget",
        "lead-42",
        name="Lead 42",
    )
    conversation_id = uuid4()
    recorded = store.record_chat_turn(
        tenant_id=tenant_uuid,
        agent_id=agent.id,
        conversation_id=conversation_id,
        channel="web_widget",
        customer_text="Hello",
        customer_id=customer.id,
    )
    assert recorded is not None

    blocked_response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Manual follow-up"},
    )

    assert blocked_response.status_code == 409
    assert "consent" in blocked_response.json()["detail"].lower()
    detail = store.get_conversation_detail(tenant_uuid, conversation_id)
    assert detail is not None
    _conversation, messages, _sources = detail
    assert all(message.content != "Manual follow-up" for message in messages)

    store.record_contact_consent(
        tenant_uuid,
        "web_widget",
        "external_id",
        "lead-42",
        source="qa",
    )

    allowed_response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Manual follow-up"},
    )

    assert allowed_response.status_code == 200
    assert allowed_response.json()["content"] == "Manual follow-up"


def test_outbound_call_blocks_suppressed_phone() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    token, tenant_id = _register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}

    store = get_app_store()
    tenant_uuid = UUID(tenant_id)

    agent = store.create_agent(
        tenant_uuid,
        AgentCreateRequest(
            name="DNC voice agent",
            prompt="Помогай клиентам и соблюдай opt-out правила.",
            channel="voice",
        ),
    )
    store.record_contact_suppression(
        tenant_uuid,
        "voice",
        "phone",
        "+79990000001",
        reason="manual_test",
        source="qa",
    )

    response = client.post(
        "/api/v1/voice/calls/outbound",
        headers=headers,
        json={"agent_id": str(agent.id), "to_number": "+7 (999) 000-00-01"},
    )

    assert response.status_code == 409
    assert "opted out" in response.json()["detail"]


def test_outbound_call_requires_contact_consent_when_policy_enabled() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    token, tenant_id = _register_owner(client)
    headers = {"Authorization": f"Bearer {token}"}

    store = get_app_store()
    tenant_uuid = UUID(tenant_id)
    store.update_tenant_settings(
        tenant_uuid,
        {
            CHANNEL_POLICIES_SETTINGS_KEY: ChannelPoliciesSettings(
                voice=ChannelCompliancePolicySettings(
                    require_contact_consent_for_outbound=True,
                )
            ).model_dump(mode="json")
        },
    )

    agent = store.create_agent(
        tenant_uuid,
        AgentCreateRequest(
            name="Consent voice agent",
            prompt="Call only contacts with recorded outbound consent.",
            channel="voice",
        ),
    )

    response = client.post(
        "/api/v1/voice/calls/outbound",
        headers=headers,
        json={"agent_id": str(agent.id), "to_number": "+7 (999) 000-00-02"},
    )

    assert response.status_code == 409
    assert "consent" in response.json()["detail"].lower()
