from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.channel_policy import (
    AUTO_REPLY_LIMIT_REACHED_STATUS,
    CHANNEL_POLICIES_SETTINGS_KEY,
    OPT_OUT_NOTICE_TEXT,
)
from app.channels import SendResult
from app.encryption import encrypt_token
from app.main import create_app
from app.schemas import (
    AgentCreateRequest,
    AgentUpdateRequest,
    ChannelAutomationMode,
    ChannelCompliancePolicySettings,
    ChannelPoliciesSettings,
    RegisterRequest,
)
from app.security import issue_access_token
from app.settings import get_settings
from app.store_factory import get_app_store

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _auth_header() -> dict[str, str]:
    store = get_app_store()
    token_secret = get_settings().access_token_secret
    if hasattr(store, "users"):
        for user in store.users.values():
            if user.tenant_id == UUID(DEMO_TENANT_ID) and user.role.value == "owner":
                token = issue_access_token(UUID(DEMO_TENANT_ID), user.id, token_secret)
                return {"Authorization": f"Bearer {token}"}
    else:
        with store.session_factory() as session:
            from sqlalchemy import select

            from app.db_models import MembershipModel, UserModel

            user_model = session.scalars(
                select(UserModel)
                .join(MembershipModel, UserModel.id == MembershipModel.user_id)
                .where(MembershipModel.tenant_id == DEMO_TENANT_ID)
                .where(MembershipModel.role == "owner")
            ).first()
            if user_model:
                token = issue_access_token(
                    UUID(DEMO_TENANT_ID),
                    UUID(user_model.id),
                    token_secret,
                )
                return {"Authorization": f"Bearer {token}"}
    raise RuntimeError("Demo owner not found")


def test_channel_policy_endpoint_round_trips_and_merges_settings() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    headers = _auth_header()

    seed_settings = client.post(
        f"/api/v1/tenants/{DEMO_TENANT_ID}/settings",
        headers=headers,
        json={"settings": {"telegram_bot_token": "telegram-token"}},
    )
    assert seed_settings.status_code == 200

    response = client.post(
        f"/api/v1/tenants/{DEMO_TENANT_ID}/settings/channel-policies",
        headers=headers,
        json={
            "telegram": {"mode": "human_approval", "ai_disclosure_required": True},
            "vk": {"mode": "draft_only"},
            "voice": {"outbound_enabled": False},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["telegram"]["mode"] == "human_approval"
    assert payload["telegram"]["ai_disclosure_required"] is True
    assert payload["vk"]["mode"] == "draft_only"
    assert payload["voice"]["outbound_enabled"] is False

    settings_response = client.post(
        f"/api/v1/tenants/{DEMO_TENANT_ID}/settings",
        headers=headers,
        json={"settings": {"vk_group_token": "vk-token"}},
    )
    assert settings_response.status_code == 200
    settings_payload = settings_response.json()
    assert settings_payload["telegram_bot_token"] == "telegram-token"
    assert settings_payload["vk_group_token"] == "vk-token"
    assert settings_payload[CHANNEL_POLICIES_SETTINGS_KEY]["telegram"]["mode"] == "human_approval"

    audit_response = client.get("/api/v1/audit-logs", headers=headers)
    assert audit_response.status_code == 200
    assert any(
        event["event_type"] == "tenant.channel_policies.updated"
        for event in audit_response.json()
    )


def test_widget_draft_only_policy_persists_draft_without_customer_reply() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    store = get_app_store()

    tenant, _user, _token = store.register(
        RegisterRequest(
            company_name="Widget Policy Tenant",
            owner_email=f"widget_policy_{uuid4().hex}@example.com",
            owner_name="Widget Owner",
            password="safe-password-123",
        ),
        "test-secret",
    )
    store.update_tenant_settings(
        tenant.id,
        {
            CHANNEL_POLICIES_SETTINGS_KEY: ChannelPoliciesSettings(
                web_widget=ChannelCompliancePolicySettings(
                    mode=ChannelAutomationMode.draft_only,
                )
            ).model_dump(mode="json")
        },
    )
    agent = store.create_agent(
        tenant.id,
        AgentCreateRequest(
            name="Widget Policy Agent",
            prompt="Отвечай из базы знаний и передавай сложные вопросы оператору.",
            channel="web_widget",
        ),
    )

    response = client.post(
        f"/api/v1/widget/chat/{agent.id}",
        json={"session_id": f"policy-session-{uuid4().hex}", "message": "Здравствуйте"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "draft_only"
    assert response.json()["response"] == ""

    conversations = store.list_conversations(tenant.id)
    assert len(conversations) == 1
    assert conversations[0].status.value == "escalated"
    assert conversations[0].resolution_status == "channel_policy_draft_only"
    assert store.list_audit_logs(tenant.id)[0].event_type == "channel_policy.auto_reply_blocked"


def test_widget_auto_reply_limit_blocks_first_customer_reply() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    store = get_app_store()

    tenant, _user, _token = store.register(
        RegisterRequest(
            company_name="Widget Limit Tenant",
            owner_email=f"widget_limit_{uuid4().hex}@example.com",
            owner_name="Widget Owner",
            password="safe-password-123",
        ),
        "test-secret",
    )
    store.update_tenant_settings(
        tenant.id,
        {
            CHANNEL_POLICIES_SETTINGS_KEY: ChannelPoliciesSettings(
                web_widget=ChannelCompliancePolicySettings(
                    max_auto_replies_per_conversation=0,
                )
            ).model_dump(mode="json")
        },
    )
    agent = store.create_agent(
        tenant.id,
        AgentCreateRequest(
            name="Widget Limit Agent",
            prompt="Answer briefly and escalate when automated reply limits are reached.",
            channel="web_widget",
        ),
    )

    response = client.post(
        f"/api/v1/widget/chat/{agent.id}",
        json={"session_id": f"limit-session-{uuid4().hex}", "message": "Hello"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "auto_reply_limit_reached"
    assert response.json()["response"] == ""

    conversations = store.list_conversations(tenant.id)
    assert len(conversations) == 1
    assert conversations[0].status.value == "escalated"
    assert conversations[0].resolution_status == AUTO_REPLY_LIMIT_REACHED_STATUS
    audit_log = store.list_audit_logs(tenant.id)[0]
    assert audit_log.event_type == "channel_policy.auto_reply_blocked"
    assert audit_log.details["block_reason"] == "auto_reply_limit"
    assert audit_log.details["agent_reply_count"] == "0"


def test_vk_human_approval_policy_blocks_external_auto_send() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    store = get_app_store()

    tenant, _user, _token = store.register(
        RegisterRequest(
            company_name="VK Policy Tenant",
            owner_email=f"vk_policy_{uuid4().hex}@example.com",
            owner_name="VK Owner",
            password="safe-password-123",
        ),
        "test-secret",
    )
    store.update_tenant_settings(
        tenant.id,
        {
            "vk_group_token": "vk_group_token_abc",
            CHANNEL_POLICIES_SETTINGS_KEY: ChannelPoliciesSettings(
                vk=ChannelCompliancePolicySettings(
                    mode=ChannelAutomationMode.human_approval,
                )
            ).model_dump(mode="json"),
        },
    )
    agent = store.create_agent(
        tenant.id,
        AgentCreateRequest(
            name="VK Policy Agent",
            prompt="Привет! Я бот поддержки VK.",
            channel="vk",
        ),
    )
    store.publish_agent(tenant.id, agent.id)

    payload = {
        "type": "message_new",
        "object": {
            "message": {
                "peer_id": 123456,
                "text": "Нужна консультация",
                "conversation_message_id": 987,
            }
        },
    }

    with patch("app.channels.vk_adapter.VKChannelAdapter.send_message") as mock_send:
        mock_send.return_value = SendResult(success=True, external_message_id="vk_msg_1")
        response = client.post(f"/api/v1/webhooks/vk/{tenant.id}", json=payload)
        assert response.status_code == 200
        assert response.text == "ok"
        assert not mock_send.called

    conversations = store.list_conversations(tenant.id)
    assert len(conversations) == 1
    assert conversations[0].status.value == "escalated"
    assert conversations[0].resolution_status == "channel_policy_human_approval_required"
    assert store.list_audit_logs(tenant.id)[0].event_type == "channel_policy.auto_reply_blocked"


def test_telegram_opt_out_notice_is_appended_to_auto_reply() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    store = get_app_store()

    tenant, _user, _token = store.register(
        RegisterRequest(
            company_name="Telegram Opt Out Tenant",
            owner_email=f"telegram_notice_{uuid4().hex}@example.com",
            owner_name="Telegram Owner",
            password="safe-password-123",
        ),
        "test-secret",
    )
    store.update_tenant_settings(
        tenant.id,
        {
            CHANNEL_POLICIES_SETTINGS_KEY: ChannelPoliciesSettings(
                telegram=ChannelCompliancePolicySettings(require_opt_out_notice=True)
            ).model_dump(mode="json"),
        },
    )
    agent = store.create_agent(
        tenant.id,
        AgentCreateRequest(
            name="Telegram Notice Agent",
            prompt="Answer as a concise support assistant.",
            channel="telegram",
        ),
    )
    plain_token = "fake_token"
    store.update_agent(
        tenant.id,
        agent.id,
        AgentUpdateRequest(
            telegram_bot_token=encrypt_token(plain_token, get_settings().access_token_secret),
        ),
    )

    payload = {
        "update_id": int(uuid4().int % 1_000_000_000),
        "message": {
            "message_id": 77,
            "chat": {"id": 1234567, "type": "private"},
            "from": {"id": 1234567, "first_name": "Policy"},
            "text": "Need help",
        },
    }

    import hashlib

    expected_secret = hashlib.sha256(plain_token.encode("utf-8")).hexdigest()
    with patch("app.channels.telegram_adapter.TelegramChannelAdapter.send_message") as mock_send:
        mock_send.return_value = SendResult(success=True, external_message_id="telegram_msg_1")
        response = client.post(
            f"/api/v1/webhooks/telegram/{agent.id}",
            json=payload,
            headers={"x-telegram-bot-api-secret-token": expected_secret},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert mock_send.called
        outbound = mock_send.call_args.args[0]
        assert OPT_OUT_NOTICE_TEXT in outbound.text

    conversations = store.list_conversations(tenant.id)
    assert len(conversations) == 1
    conversation_detail = store.get_conversation_detail(tenant.id, conversations[0].id)
    assert conversation_detail is not None
    _conversation, messages, _sources = conversation_detail
    assert any(OPT_OUT_NOTICE_TEXT in message.content for message in messages)
