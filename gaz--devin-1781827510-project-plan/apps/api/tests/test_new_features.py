"""
Tests for Team management, Analytics, and API keys endpoints.
"""

from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _auth_header(store) -> dict[str, str]:
    """Get auth header for demo owner."""
    from app.security import issue_access_token

    token_secret = get_settings().access_token_secret
    if hasattr(store, "users"):
        # InMemoryStore
        for user in store.users.values():
            if user.tenant_id == UUID(DEMO_TENANT_ID) and user.role.value == "owner":
                token = issue_access_token(
                    UUID(DEMO_TENANT_ID),
                    user.id,
                    token_secret,
                )
                return {"Authorization": f"Bearer {token}"}
    else:
        # SqlAlchemyStore
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


def test_team_members_list():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    headers = _auth_header(store)  # type: ignore[arg-type]

    response = client.get("/api/v1/team/members", headers=headers)
    assert response.status_code == 200
    members = response.json()
    assert isinstance(members, list)
    assert len(members) >= 1  # At least demo owner
    # Check structure
    first = members[0]
    assert "id" in first
    assert "email" in first
    assert "name" in first
    assert "role" in first


def test_team_invite_new_member():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    headers = _auth_header(store)  # type: ignore[arg-type]

    response = client.post(
        "/api/v1/team/invite",
        json={"email": "newuser@test.com", "name": "Test User", "role": "viewer"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "newuser@test.com"
    assert data["user"]["role"] == "viewer"
    assert "invite_token" in data


def test_team_invite_duplicate_rejected():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    headers = _auth_header(store)  # type: ignore[arg-type]

    # First invite
    client.post(
        "/api/v1/team/invite",
        json={"email": "dup@test.com", "name": "Dup User", "role": "viewer"},
        headers=headers,
    )
    # Second invite with same email
    response = client.post(
        "/api/v1/team/invite",
        json={"email": "dup@test.com", "name": "Dup User 2", "role": "admin"},
        headers=headers,
    )
    assert response.status_code == 409


def test_analytics_overview():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    headers = _auth_header(store)  # type: ignore[arg-type]

    response = client.get("/api/v1/analytics/overview", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_conversations" in data
    assert "automation_rate" in data
    assert "conversations_by_channel" in data
    assert "conversations_by_day" in data
    assert "top_unresolved" in data
    assert isinstance(data["conversations_by_day"], list)
    assert len(data["conversations_by_day"]) == 30  # 30 days


def test_analytics_agents():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    headers = _auth_header(store)  # type: ignore[arg-type]

    response = client.get("/api/v1/analytics/agents", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        agent = data[0]
        assert "agent_id" in agent
        assert "agent_name" in agent
        assert "automation_rate" in agent


def test_api_keys_crud():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    headers = _auth_header(store)  # type: ignore[arg-type]

    # Create key
    response = client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "scopes": ["read", "write"]},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Key"
    assert data["key"].startswith("cf_live_")
    assert "message" in data
    key_id = data["id"]

    # List keys
    response = client.get("/api/v1/api-keys", headers=headers)
    assert response.status_code == 200
    keys = response.json()
    assert any(k["id"] == key_id for k in keys)

    # Revoke key
    response = client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
    assert response.status_code == 204

    # Verify revoked
    response = client.get("/api/v1/api-keys", headers=headers)
    keys = response.json()
    revoked = next((k for k in keys if k["id"] == key_id), None)
    assert revoked is not None
    assert revoked["revoked"] is True


def test_telegram_webhook_handles_valid_message():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()

    # Get demo agent ID
    agents = store.list_agents(UUID(DEMO_TENANT_ID))
    if not agents:
        return  # Skip if no demo agents
    agent_id = str(agents[0].id)

    # Simulate Telegram update
    update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "chat": {"id": 12345, "type": "private"},
            "from": {"id": 12345, "first_name": "Test", "last_name": "User"},
            "text": "Привет, какое у вас меню?",
        },
    }

    response = client.post(f"/api/v1/webhooks/telegram/{agent_id}", json=update)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_telegram_webhook_deduplicates():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()

    agents = store.list_agents(UUID(DEMO_TENANT_ID))
    if not agents:
        return
    agent_id = str(agents[0].id)

    update = {
        "update_id": 999888777,
        "message": {
            "message_id": 2,
            "chat": {"id": 12345, "type": "private"},
            "from": {"id": 12345, "first_name": "Test"},
            "text": "Дубликат",
        },
    }

    # First request
    r1 = client.post(f"/api/v1/webhooks/telegram/{agent_id}", json=update)
    assert r1.status_code == 200

    # Second request with same update_id - should be deduped
    r2 = client.post(f"/api/v1/webhooks/telegram/{agent_id}", json=update)
    assert r2.status_code == 200
    assert r2.json().get("detail") == "duplicate"


def test_widget_chat_endpoint():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    agents = store.list_agents(UUID(DEMO_TENANT_ID))
    if not agents:
        return
    agent_id = str(agents[0].id)

    response = client.post(
        f"/api/v1/widget/chat/{agent_id}",
        json={
            "session_id": "test_widget_session_123",
            "message": "Привет из виджета!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 0
    assert "conversation_id" in data


def test_widget_chat_reuses_session_conversation():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    agents = store.list_agents(UUID(DEMO_TENANT_ID))
    if not agents:
        return
    agent_id = str(agents[0].id)
    session_id = "test_widget_session_history_123"

    first = client.post(
        f"/api/v1/widget/chat/{agent_id}",
        json={"session_id": session_id, "message": "Первое сообщение"},
    )
    second = client.post(
        f"/api/v1/widget/chat/{agent_id}",
        json={"session_id": session_id, "message": "Второе сообщение"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["conversation_id"] == second_payload["conversation_id"]

    detail = store.get_conversation_detail(
        UUID(DEMO_TENANT_ID),
        UUID(first_payload["conversation_id"]),
    )
    assert detail is not None
    _, messages, _ = detail
    assert [message.content for message in messages[-4:]] == [
        "Первое сообщение",
        first_payload["response"],
        "Второе сообщение",
        second_payload["response"],
    ]


def test_cors_origins_are_configurable(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://widget.example.test")
    get_settings.cache_clear()
    try:
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.options(
            "/api/v1/widget/chat/389a4f13-05d3-5860-af9f-69bd9ce2493a",
            headers={
                "Access-Control-Request-Headers": "content-type",
                "Access-Control-Request-Method": "POST",
                "Origin": "http://widget.example.test",
            },
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://widget.example.test"
