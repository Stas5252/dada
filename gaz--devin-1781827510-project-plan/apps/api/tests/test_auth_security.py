from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pyotp
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.v1.dependencies import AuthContext, require_permission, resolve_current_principal
from app.audit import AuditAction, build_audit_event
from app.contracts.masking import MASKED_VALUE
from app.main import create_app
from app.rbac import (
    Permission,
    PermissionDeniedError,
    Role,
    assert_role_allowed,
    role_has_permission,
)
from app.security import issue_access_token

MANAGE_AGENTS_DEPENDENCY = require_permission(Permission.MANAGE_AGENTS)


@dataclass(frozen=True)
class RegisteredUser:
    tenant_id: str
    user_id: str
    token: str
    refresh_token: str


def test_bearer_token_resolves_tenant_and_user_context() -> None:
    client = _auth_client()
    registered = _register_user(client, "resolve")

    response = client.get(
        "/__test__/auth-context",
        headers={"Authorization": f"Bearer {registered.token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "tenant_id": registered.tenant_id,
        "user_id": registered.user_id,
        "role": Role.owner,
    }


def test_register_returns_jwt_access_token_and_refresh_token() -> None:
    client = _auth_client()
    registered = _register_user(client, "token-pair")

    assert len(registered.token.split(".")) == 3
    assert not registered.token.startswith("devin-local.")
    assert registered.refresh_token.startswith("gaz-refresh.")


@pytest.mark.parametrize(
    "token",
    [
        "not-a-token",
        "devin-local.invalid.invalid",
    ],
)
def test_invalid_bearer_token_is_rejected(token: str) -> None:
    client = _auth_client()

    response = client.get(
        "/__test__/auth-context",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"]["error_code"] == "INVALID_ACCESS_TOKEN"


def test_expired_bearer_token_is_rejected() -> None:
    client = _auth_client()
    registered = _register_user(client, "expired")
    expired_token = issue_access_token(
        UUID(registered.tenant_id),
        UUID(registered.user_id),
        "local-development-token-secret",
        ttl_minutes=-1,
    )

    response = client.get(
        "/__test__/auth-context",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "INVALID_ACCESS_TOKEN"


def test_tampered_bearer_token_is_rejected() -> None:
    client = _auth_client()
    registered = _register_user(client, "tampered")
    prefix, payload, signature = registered.token.split(".")
    replacement = "A" if payload[-1] != "A" else "B"
    tampered_token = f"{prefix}.{payload[:-1]}{replacement}.{signature}"

    response = client.get(
        "/__test__/auth-context",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "INVALID_ACCESS_TOKEN"


def test_tenant_header_must_match_bearer_token_tenant() -> None:
    client = _auth_client()
    first = _register_user(client, "tenant-mismatch-a")
    second = _register_user(client, "tenant-mismatch-b")

    response = client.get(
        "/__test__/auth-context",
        headers={
            "Authorization": f"Bearer {first.token}",
            "x-tenant-id": second.tenant_id,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "TENANT_TOKEN_MISMATCH"


def test_refresh_rotates_session_and_rejects_refresh_token_reuse() -> None:
    client = _auth_client()
    registered = _register_user(client, "refresh-rotation")

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered.refresh_token},
    )

    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert refresh_payload["access_token"] != registered.token
    assert refresh_payload["refresh_token"] != registered.refresh_token

    context_response = client.get(
        "/__test__/auth-context",
        headers={"Authorization": f"Bearer {refresh_payload['access_token']}"},
    )
    assert context_response.status_code == 200
    assert context_response.json()["user_id"] == registered.user_id

    reuse_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered.refresh_token},
    )
    assert reuse_response.status_code == 401
    assert reuse_response.json()["detail"]["error_code"] == "INVALID_REFRESH_TOKEN"


def test_logout_revokes_refresh_token() -> None:
    client = _auth_client()
    registered = _register_user(client, "logout")

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": registered.refresh_token},
    )
    assert logout_response.status_code == 204

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered.refresh_token},
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"]["error_code"] == "INVALID_REFRESH_TOKEN"


def test_auth_user_responses_do_not_expose_totp_secret() -> None:
    client = _auth_client()
    email = f"mfa-public-{uuid4()}@example.com"
    password = "safe-local-password"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "MFA Public Tenant",
            "owner_email": email,
            "owner_name": "Security Owner",
            "password": password,
        },
    )
    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["user"]["mfa_enabled"] is False
    assert register_payload["user"]["mfa_recovery_codes_remaining"] == 0
    assert "totp_secret" not in register_payload["user"]

    headers = {"Authorization": f"Bearer {register_payload['access_token']}"}
    setup_response = client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_response.status_code == 200
    secret = setup_response.json()["secret"]

    verify_response = client.post(
        "/api/v1/auth/mfa/verify",
        headers=headers,
        json={"secret": secret, "code": pyotp.TOTP(secret).now()},
    )
    assert verify_response.status_code == 200
    recovery_codes = verify_response.json()["codes"]
    assert len(recovery_codes) == 8
    assert all(len(code) == 9 and "-" in code for code in recovery_codes)

    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["mfa_enabled"] is True
    assert me_payload["mfa_recovery_codes_remaining"] == 8
    assert "totp_secret" not in me_payload

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["requires_mfa"] is True
    assert login_payload["access_token"]

    mfa_response = client.post(
        "/api/v1/auth/login/mfa",
        json={"token": login_payload["access_token"], "code": pyotp.TOTP(secret).now()},
    )
    assert mfa_response.status_code == 200
    mfa_payload = mfa_response.json()
    assert mfa_payload["user"]["mfa_enabled"] is True
    assert mfa_payload["user"]["mfa_recovery_codes_remaining"] == 8
    assert "totp_secret" not in mfa_payload["user"]


def test_mfa_recovery_codes_are_single_use_and_can_disable_mfa() -> None:
    client = _auth_client()
    email = f"mfa-recovery-{uuid4()}@example.com"
    password = "safe-local-password"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "MFA Recovery Tenant",
            "owner_email": email,
            "owner_name": "Security Owner",
            "password": password,
        },
    )
    assert register_response.status_code == 201
    register_payload = register_response.json()
    headers = {"Authorization": f"Bearer {register_payload['access_token']}"}

    setup_response = client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_response.status_code == 200
    secret = setup_response.json()["secret"]

    verify_response = client.post(
        "/api/v1/auth/mfa/verify",
        headers=headers,
        json={"secret": secret, "code": pyotp.TOTP(secret).now()},
    )
    assert verify_response.status_code == 200
    recovery_codes = verify_response.json()["codes"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["requires_mfa"] is True

    recovery_login_response = client.post(
        "/api/v1/auth/login/mfa",
        json={"token": login_payload["access_token"], "code": recovery_codes[0]},
    )
    assert recovery_login_response.status_code == 200
    recovery_login_payload = recovery_login_response.json()
    assert recovery_login_payload["user"]["mfa_recovery_codes_remaining"] == 7

    second_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert second_login_response.status_code == 200
    reused_code_response = client.post(
        "/api/v1/auth/login/mfa",
        json={"token": second_login_response.json()["access_token"], "code": recovery_codes[0]},
    )
    assert reused_code_response.status_code == 401

    session_headers = {
        "Authorization": f"Bearer {recovery_login_payload['access_token']}",
    }
    regenerate_response = client.post(
        "/api/v1/auth/mfa/recovery-codes",
        headers=session_headers,
        json={"code": pyotp.TOTP(secret).now()},
    )
    assert regenerate_response.status_code == 200
    regenerated_codes = regenerate_response.json()["codes"]
    assert len(regenerated_codes) == 8
    assert regenerated_codes != recovery_codes

    disable_response = client.post(
        "/api/v1/auth/mfa/disable",
        headers=session_headers,
        json={"code": regenerated_codes[0]},
    )
    assert disable_response.status_code == 204

    me_response = client.get("/api/v1/auth/me", headers=session_headers)
    assert me_response.status_code == 200
    assert me_response.json()["mfa_enabled"] is False
    assert me_response.json()["mfa_recovery_codes_remaining"] == 0

    password_login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert password_login_response.status_code == 200
    assert password_login_response.json()["requires_mfa"] is False


def test_tampered_refresh_token_is_rejected() -> None:
    client = _auth_client()
    registered = _register_user(client, "bad-refresh")
    prefix, session_id, verifier = registered.refresh_token.split(".")
    replacement = "A" if verifier[-1] != "A" else "B"
    tampered_token = f"{prefix}.{session_id}.{verifier[:-1]}{replacement}"

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tampered_token},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "INVALID_REFRESH_TOKEN"


def test_business_endpoint_accepts_bearer_token_without_tenant_header() -> None:
    client = TestClient(create_app())
    registered = _register_user(client, "business-bearer")

    response = client.post(
        "/api/v1/agents",
        headers={"Authorization": f"Bearer {registered.token}"},
        json={
            "name": "Bearer Agent",
            "prompt": "Answer from approved knowledge and escalate unknown requests.",
            "channel": "web_widget",
        },
    )

    assert response.status_code == 201
    assert response.json()["tenant_id"] == registered.tenant_id


def test_business_endpoint_rejects_bearer_tenant_header_mismatch() -> None:
    client = TestClient(create_app())
    first = _register_user(client, "business-mismatch-a")
    second = _register_user(client, "business-mismatch-b")

    response = client.get(
        "/api/v1/agents",
        headers={
            "Authorization": f"Bearer {first.token}",
            "x-tenant-id": second.tenant_id,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "TENANT_TOKEN_MISMATCH"


def test_business_endpoint_blocks_legacy_tenant_header_when_disabled(monkeypatch) -> None:
    from app.settings import get_settings
    from app.store_factory import get_app_store

    monkeypatch.setenv("ALLOW_LEGACY_TENANT_HEADER", "false")
    get_settings.cache_clear()
    get_app_store.cache_clear()
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/agents",
        headers={"x-tenant-id": str(uuid4())},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "INVALID_ACCESS_TOKEN"
    get_settings.cache_clear()
    get_app_store.cache_clear()


def test_role_policy_allows_owner_and_blocks_viewer_for_agent_management() -> None:
    assert role_has_permission(Role.owner, Permission.MANAGE_AGENTS)
    assert not role_has_permission(Role.viewer, Permission.MANAGE_AGENTS)

    with pytest.raises(PermissionDeniedError):
        assert_role_allowed(Role.viewer, Permission.MANAGE_AGENTS)


def test_role_dependency_blocks_insufficient_role() -> None:
    from app.store_factory import get_app_store
    active_store = get_app_store()
    client = _rbac_client()
    registered = _register_user(client, "viewer")
    user = active_store.get_user(UUID(registered.user_id))
    assert user is not None
    if hasattr(active_store, "users"):
        active_store.users[user.id] = user.model_copy(update={"role": Role.viewer})
    else:
        with active_store.session_factory() as session:
            from sqlalchemy import select

            from app.db_models import MembershipModel
            membership = session.scalars(
                select(MembershipModel)
                .where(MembershipModel.user_id == str(user.id))
            ).first()
            if membership:
                membership.role = "viewer"
                session.commit()

    response = client.post(
        "/__test__/manage-agents",
        headers={"Authorization": f"Bearer {registered.token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "ROLE_PERMISSION_DENIED"


def test_business_endpoint_blocks_viewer_from_agent_management() -> None:
    from app.store_factory import get_app_store
    active_store = get_app_store()
    client = TestClient(create_app())
    registered = _register_user(client, "viewer-business")
    user = active_store.get_user(UUID(registered.user_id))
    assert user is not None
    if hasattr(active_store, "users"):
        active_store.users[user.id] = user.model_copy(update={"role": Role.viewer})
    else:
        with active_store.session_factory() as session:
            from sqlalchemy import select

            from app.db_models import MembershipModel
            membership = session.scalars(
                select(MembershipModel)
                .where(MembershipModel.user_id == str(user.id))
            ).first()
            if membership:
                membership.role = "viewer"
                session.commit()

    response = client.post(
        "/api/v1/agents",
        headers={"Authorization": f"Bearer {registered.token}"},
        json={
            "name": "Viewer Agent",
            "prompt": "Answer from approved knowledge and escalate unknown requests.",
            "channel": "web_widget",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "ROLE_PERMISSION_DENIED"


def test_audit_event_masks_pii_in_auth_agent_knowledge_and_chat_metadata() -> None:
    tenant_id = uuid4()
    user_id = uuid4()

    event = build_audit_event(
        action=AuditAction.CHAT_MOCK,
        outcome="success",
        tenant_id=tenant_id,
        user_id=user_id,
        actor_role=Role.agent,
        metadata={
            "tenant_id": str(tenant_id),
            "email": "customer@example.com",
            "token": "local-token",
            "chat": {
                "message": "Можно узнать статус заказа?",
                "customer_name": "Customer Name",
                "phone": "+79990000000",
            },
        },
    )

    assert event.resource == "chat"
    assert event.tenant_id == tenant_id
    assert event.user_id == user_id
    assert event.masked_metadata["email"] == MASKED_VALUE
    assert event.masked_metadata["token"] == MASKED_VALUE
    chat_metadata = event.masked_metadata["chat"]
    assert isinstance(chat_metadata, dict)
    assert chat_metadata["message"] == "Можно узнать статус заказа?"
    assert chat_metadata["customer_name"] == MASKED_VALUE
    assert chat_metadata["phone"] == MASKED_VALUE


def test_audit_actions_are_scoped_to_auth_agent_knowledge_and_chat() -> None:
    assert {action.value.split(".")[0] for action in AuditAction} == {
        "auth",
        "agent",
        "knowledge",
        "chat",
    }


def _auth_client() -> TestClient:
    app = create_app()
    _add_auth_probe(app)
    return TestClient(app)


def _rbac_client() -> TestClient:
    app = create_app()
    _add_rbac_probe(app)
    return TestClient(app)


def _add_auth_probe(app: FastAPI) -> None:
    @app.get("/__test__/auth-context")
    async def auth_context_probe(
        auth_context: AuthContext = Depends(resolve_current_principal),  # noqa: B008
    ) -> dict[str, str]:
        return {
            "tenant_id": auth_context.tenant_id,
            "user_id": auth_context.user_id,
            "role": auth_context.role,
        }


def _add_rbac_probe(app: FastAPI) -> None:
    @app.post("/__test__/manage-agents")
    async def manage_agents_probe(
        auth_context: AuthContext = Depends(MANAGE_AGENTS_DEPENDENCY),  # noqa: B008
    ) -> dict[str, str]:
        return {"tenant_id": auth_context.tenant_id}


def _register_user(client: TestClient, email_prefix: str) -> RegisteredUser:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"{email_prefix} Tenant",
            "owner_email": f"{email_prefix}-{uuid4()}@example.com",
            "owner_name": "Security Owner",
            "password": "safe-local-password",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    return RegisteredUser(
        tenant_id=payload["tenant"]["id"],
        user_id=payload["user"]["id"],
        token=payload["access_token"],
        refresh_token=payload["refresh_token"],
    )
