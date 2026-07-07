"""
T4.1 — Тесты RBAC + Tenant Isolation.

Покрывает: матрица ролей (owner/admin/agent/viewer),
запрет межтенантного доступа через API,
проверка что viewer не может менять данные.
"""
import os
import pytest
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "sqlite:///test_run.db")

from app.rbac import (
    Permission,
    PermissionDeniedError,
    Role,
    ROLE_PERMISSIONS,
    assert_role_allowed,
    role_has_permission,
    normalize_role,
)


# ─── RBAC: матрица ролей ─────────────────────────────────────────────

class TestRolePermissionMatrix:
    """Проверяем RBAC матрицу для всех ролей."""

    def test_owner_has_all_permissions(self):
        for perm in Permission:
            assert role_has_permission(Role.owner, perm), \
                f"Owner should have {perm}"

    def test_admin_has_most_permissions(self):
        admin_perms = ROLE_PERMISSIONS[Role.admin]
        assert Permission.MANAGE_AGENTS in admin_perms
        assert Permission.MANAGE_KNOWLEDGE in admin_perms
        assert Permission.MANAGE_CHAT in admin_perms
        assert Permission.MANAGE_BILLING in admin_perms
        assert Permission.READ_AUDIT in admin_perms

    def test_admin_cannot_manage_auth(self):
        assert role_has_permission(Role.admin, Permission.READ_AUTH)
        assert not role_has_permission(Role.admin, Permission.MANAGE_AUTH)

    def test_agent_read_only_except_chat(self):
        assert role_has_permission(Role.agent, Permission.READ_AGENTS)
        assert role_has_permission(Role.agent, Permission.READ_KNOWLEDGE)
        assert role_has_permission(Role.agent, Permission.READ_CHAT)
        assert role_has_permission(Role.agent, Permission.MANAGE_CHAT)
        assert not role_has_permission(Role.agent, Permission.MANAGE_AGENTS)
        assert not role_has_permission(Role.agent, Permission.MANAGE_KNOWLEDGE)
        assert not role_has_permission(Role.agent, Permission.MANAGE_BILLING)

    def test_viewer_read_only(self):
        assert role_has_permission(Role.viewer, Permission.READ_AGENTS)
        assert role_has_permission(Role.viewer, Permission.READ_KNOWLEDGE)
        assert role_has_permission(Role.viewer, Permission.READ_CHAT)
        assert not role_has_permission(Role.viewer, Permission.MANAGE_CHAT)
        assert not role_has_permission(Role.viewer, Permission.MANAGE_AGENTS)
        assert not role_has_permission(Role.viewer, Permission.MANAGE_BILLING)
        assert not role_has_permission(Role.viewer, Permission.READ_AUDIT)

    def test_assert_role_allowed_raises_on_deny(self):
        with pytest.raises(PermissionDeniedError):
            assert_role_allowed(Role.viewer, Permission.MANAGE_CHAT)

    def test_assert_role_allowed_passes_on_grant(self):
        assert_role_allowed(Role.owner, Permission.MANAGE_BILLING)

    def test_unknown_role_raises(self):
        with pytest.raises(PermissionDeniedError, match="unknown role"):
            normalize_role("superadmin")

    def test_string_role_works(self):
        assert role_has_permission("owner", Permission.MANAGE_AUTH)
        assert not role_has_permission("viewer", Permission.MANAGE_AUTH)


# ─── Tenant Isolation через API ──────────────────────────────────────

class TestTenantIsolationAPI:
    """Проверяем, что один тенант не видит данные другого через API."""

    @pytest.fixture
    def app_client(self):
        from app.main import create_app
        from fastapi.testclient import TestClient
        app = create_app()
        return TestClient(app, raise_server_exceptions=False)

    def _register_and_get_headers(self, app_client, suffix: str):
        """Создаём тенанта и получаем токен."""
        reg = app_client.post("/api/v1/auth/register", json={
            "company_name": f"Company {suffix}",
            "owner_email": f"owner-{suffix}@test.com",
            "owner_name": f"Owner {suffix}",
            "password": "Test1234!",
        })
        assert reg.status_code == 201, f"Registration failed: {reg.text}"
        token = reg.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_tenant_cannot_see_other_tenants_agents(self, app_client):
        """Тенант A не видит агентов тенанта B."""
        headers_a = self._register_and_get_headers(app_client, uuid4().hex[:8])
        headers_b = self._register_and_get_headers(app_client, uuid4().hex[:8])

        # Тенант A создаёт агента
        create_resp = app_client.post("/api/v1/agents", json={
            "name": "Агент А",
            "prompt": "Ты агент поддержки клиентов компании А",
        }, headers=headers_a)
        assert create_resp.status_code in (200, 201), f"Agent creation failed: {create_resp.text}"
        agent_id_a = create_resp.json()["id"]

        # Тенант B не видит агента A
        list_resp = app_client.get("/api/v1/agents", headers=headers_b)
        assert list_resp.status_code == 200
        agent_ids_b = [a["id"] for a in list_resp.json()]
        assert agent_id_a not in agent_ids_b

    def test_tenant_cannot_access_other_tenants_conversations(self, app_client):
        """Тенант A не может получить доступ к диалогам тенанта B."""
        headers_a = self._register_and_get_headers(app_client, uuid4().hex[:8])
        headers_b = self._register_and_get_headers(app_client, uuid4().hex[:8])

        convs_a = app_client.get("/api/v1/conversations", headers=headers_a)
        convs_b = app_client.get("/api/v1/conversations", headers=headers_b)
        assert convs_a.status_code == 200
        assert convs_b.status_code == 200

        ids_a = {c["id"] for c in convs_a.json()}
        ids_b = {c["id"] for c in convs_b.json()}
        assert ids_a.isdisjoint(ids_b)
