from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _auth_header(store, role="owner") -> dict[str, str]:
    """Get auth header for demo owner or other roles."""
    from app.security import issue_access_token
    token_secret = get_settings().access_token_secret
    if hasattr(store, "users"):
        # InMemoryStore
        for user in store.users.values():
            if user.tenant_id == UUID(DEMO_TENANT_ID) and user.role.value == role:
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
                .where(MembershipModel.role == role)
            ).first()
            if user_model:
                token = issue_access_token(
                    UUID(DEMO_TENANT_ID),
                    UUID(user_model.id),
                    token_secret,
                )
                return {"Authorization": f"Bearer {token}"}
    raise RuntimeError(f"Demo {role} not found")


def test_audit_logs_list():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    headers = _auth_header(store, role="owner")

    # Create dummy audit log
    store.create_audit_log(
        event_type="test_event",
        tenant_id=UUID(DEMO_TENANT_ID),
        details={"foo": "bar"}
    )

    response = client.get("/api/v1/audit-logs", headers=headers)
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1
    assert any(log["event_type"] == "test_event" for log in logs)


def test_audit_logs_rbac_denied():
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)
    from app.store_factory import get_app_store

    store = get_app_store()
    # A viewer role doesn't have Permission.READ_AUDIT
    try:
        headers = _auth_header(store, role="viewer")
    except RuntimeError:
        owner_headers = _auth_header(store, role="owner")
        client.post(
            "/api/v1/team/invite",
            json={"email": "viewer_rbac_test@test.com", "name": "Viewer Test", "role": "viewer"},
            headers=owner_headers,
        )
        headers = _auth_header(store, role="viewer")

    response = client.get("/api/v1/audit-logs", headers=headers)
    assert response.status_code == 403
