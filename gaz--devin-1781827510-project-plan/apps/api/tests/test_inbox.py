from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"

def _auth_header(store) -> dict[str, str]:
    from app.security import issue_access_token
    token_secret = get_settings().access_token_secret
    if hasattr(store, "users"):
        for user in store.users.values():
            if user.tenant_id == UUID(DEMO_TENANT_ID) and user.role.value == "owner":
                token = issue_access_token(
                    UUID(DEMO_TENANT_ID),
                    user.id,
                    token_secret,
                )
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


def test_inbox_api():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.schemas import AgentCreateRequest
    from app.store_factory import get_app_store

    store = get_app_store()
    headers = _auth_header(store)

    # Fetch user_id for assignment
    with store.session_factory() as session:
        from app.db_models import UserModel
        user = session.query(UserModel).first()
        user_id = user.id

    # Create agent
    agent = store.create_agent(
        UUID(DEMO_TENANT_ID),
        AgentCreateRequest(name="Inbox Agent", prompt="Test Prompt")
    )

    # Create mock conversation
    chat_response = client.post(
        "/api/v1/chat/mock",
        headers=headers,
        json={
            "agent_id": str(agent.id),
            "channel": "web_widget",
            "message": "Привет",
        },
    )
    assert chat_response.status_code == 201
    conv_id = chat_response.json()["conversation"]["id"]

    # Test list inbox conversations
    resp = client.get("/api/v1/inbox/conversations", headers=headers)
    assert resp.status_code == 200
    convs = resp.json()
    assert isinstance(convs, list)
    # Check if the conversation is there and has handoff_status
    found = next((c for c in convs if c["id"] == conv_id), None)
    assert found is not None
    assert found["handoff_status"] == "ai_handling"

    # Test assign
    assign_resp = client.post(
        f"/api/v1/inbox/conversations/{conv_id}/assign",
        headers=headers,
        json={"user_id": user_id}
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["handoff_status"] == "assigned"
    assert assign_resp.json()["assigned_user_id"] == str(user_id)

    # Test return to AI
    return_resp = client.post(
        f"/api/v1/inbox/conversations/{conv_id}/return",
        headers=headers
    )
    assert return_resp.status_code == 200
    assert return_resp.json()["handoff_status"] == "ai_handling"
    assert return_resp.json()["assigned_user_id"] is None

    # Test add tag
    tag_resp = client.post(
        f"/api/v1/inbox/conversations/{conv_id}/tags",
        headers=headers,
        json={"tag_name": "VIP"}
    )
    assert tag_resp.status_code == 200
    assert tag_resp.json()["tag_name"] == "VIP"

    # Test remove tag
    del_resp = client.delete(
        f"/api/v1/inbox/conversations/{conv_id}/tags/VIP",
        headers=headers
    )
    assert del_resp.status_code == 204

    # Test add note
    note_resp = client.post(
        f"/api/v1/inbox/conversations/{conv_id}/notes",
        headers=headers,
        json={"body": "Customer is angry"}
    )
    assert note_resp.status_code == 200
    assert note_resp.json()["body"] == "Customer is angry"
