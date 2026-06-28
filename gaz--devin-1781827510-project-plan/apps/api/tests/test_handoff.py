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


def test_conversation_handoff_and_resolve():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.schemas import AgentCreateRequest
    from app.store_factory import get_app_store

    store = get_app_store()
    headers = _auth_header(store)

    # 1. Create an agent
    agent = store.create_agent(
        UUID(DEMO_TENANT_ID),
        AgentCreateRequest(name="Handoff Agent", prompt="Test Prompt")
    )

    # 2. Start a mock conversation
    chat_response = client.post(
        "/api/v1/chat/mock",
        headers=headers,
        json={
            "agent_id": str(agent.id),
            "channel": "web_widget",
            "message": "Привет, позови человека",
        },
    )
    assert chat_response.status_code == 201
    conv_id = chat_response.json()["conversation"]["id"]

    # 3. Call handoff endpoint
    handoff_response = client.post(
        f"/api/v1/conversations/{conv_id}/handoff",
        headers=headers,
    )
    assert handoff_response.status_code == 200
    conv_data = handoff_response.json()
    assert conv_data["status"] == "escalated"
    assert conv_data["resolution_status"] == "Escalated to human operator"

    # 4. Resolve it again to verify resolve endpoint
    resolve_response = client.post(
        f"/api/v1/conversations/{conv_id}/resolve",
        headers=headers,
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "resolved"
