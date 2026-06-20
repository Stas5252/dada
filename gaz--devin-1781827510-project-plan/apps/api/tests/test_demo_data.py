from fastapi.testclient import TestClient

from app.database import build_session_factory, create_schema
from app.demo_data import DEMO_TENANT_ID
from app.main import create_app
from app.settings import Settings
from app.sqlalchemy_store import SqlAlchemyStore
from app.store import InMemoryStore


def test_memory_store_seeds_demo_data_idempotently() -> None:
    repository = InMemoryStore()

    first_tenant = repository.seed_demo_data(DEMO_TENANT_ID, "test-secret")
    second_tenant = repository.seed_demo_data(DEMO_TENANT_ID, "test-secret")

    assert first_tenant.id == DEMO_TENANT_ID
    assert second_tenant.id == DEMO_TENANT_ID
    assert len(repository.list_agents(DEMO_TENANT_ID)) == 2
    assert len(repository.list_knowledge_sources(DEMO_TENANT_ID)) == 2
    assert len(repository.list_conversations(DEMO_TENANT_ID)) == 3


def test_sqlalchemy_store_seeds_demo_data(sqlite_engine) -> None:
    create_schema(sqlite_engine)
    repository = SqlAlchemyStore(
        build_session_factory(sqlite_engine),
        Settings(database_url="sqlite+pysqlite:///:memory:"),
    )

    tenant = repository.seed_demo_data(DEMO_TENANT_ID, "test-secret")
    repository.seed_demo_data(DEMO_TENANT_ID, "test-secret")

    assert tenant.id == DEMO_TENANT_ID
    assert len(repository.list_agents(DEMO_TENANT_ID)) == 2
    assert len(repository.list_knowledge_sources(DEMO_TENANT_ID)) == 2
    assert len(repository.list_conversations(DEMO_TENANT_ID)) == 3


def test_default_demo_tenant_dashboard_is_available() -> None:
    app = create_app()
    from app.api.v1.tenants import READ_DASHBOARD

    tenant_id = str(DEMO_TENANT_ID)
    app.dependency_overrides[READ_DASHBOARD] = lambda: tenant_id
    client = TestClient(app)

    response = client.get(
        f"/api/v1/tenants/{tenant_id}/dashboard",
        headers={"x-tenant-id": tenant_id},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant"]["id"] == tenant_id
    assert payload["agents_total"] >= 2
    assert payload["knowledge_sources_total"] >= 2
    assert payload["conversations_total"] >= 3
