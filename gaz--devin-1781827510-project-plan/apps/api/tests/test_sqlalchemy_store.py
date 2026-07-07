from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.database import build_engine, build_session_factory, create_schema
from app.schemas import (
    AgentCreateRequest,
    AgentUpdateRequest,
    ChatMessageRequest,
    KnowledgeSourceCreateRequest,
    RegisterRequest,
)
from app.security import issue_refresh_token, parse_refresh_token
from app.settings import Settings
from app.sqlalchemy_store import SqlAlchemyStore


def test_sqlalchemy_store_core_mvp_flow(sqlite_engine) -> None:
    create_schema(sqlite_engine)
    repository = SqlAlchemyStore(
        build_session_factory(sqlite_engine),
        Settings(database_url="sqlite+pysqlite:///:memory:"),
    )

    tenant, user, token = repository.register(
        RegisterRequest(
            company_name="SQL Tenant",
            owner_email="sql@example.com",
            owner_name="SQL Owner",
            password="safe-local-password",
        ),
        "test-secret",
    )

    assert len(token.split(".")) == 3
    assert user.role == "owner"
    login_result = repository.login("sql@example.com", "safe-local-password", "test-secret")
    assert login_result is not None
    assert login_result[0].id == tenant.id
    assert repository.login("sql@example.com", "wrong-password", "test-secret") is None

    agent = repository.create_agent(
        tenant.id,
        AgentCreateRequest(
            name="SQL Agent",
            prompt="Answer only from knowledge base and escalate otherwise.",
            channel="web_widget",
            business_profile="B2B support desk for account questions.",
            agent_role="customer_support",
            agent_tone="concise",
            agent_language="en",
            business_hours="Mon-Fri 09:00-18:00",
            escalation_rules="Escalate billing disputes.",
            sales_rules="Do not promise custom discounts.",
            forbidden_topics=["legal advice"],
            enabled_tools=["escalate_to_human"],
        ),
    )
    assert agent.business_profile == "B2B support desk for account questions."
    assert agent.agent_role == "customer_support"
    assert agent.agent_tone == "concise"
    assert agent.agent_language == "en"
    assert agent.business_hours == "Mon-Fri 09:00-18:00"
    assert agent.escalation_rules == "Escalate billing disputes."
    assert agent.sales_rules == "Do not promise custom discounts."
    assert agent.forbidden_topics == ["legal advice"]
    assert agent.enabled_tools == ["escalate_to_human"]
    published_agent = repository.publish_agent(tenant.id, agent.id)
    assert published_agent is not None
    assert published_agent.status == "published"

    updated_agent = repository.update_agent(
        tenant.id,
        agent.id,
        AgentUpdateRequest(
            name="SQL Agent v2",
            prompt="Answer from approved SQL knowledge and escalate unknown requests.",
            channel="telegram",
            business_profile="Updated support desk profile.",
            enabled_tools=[
                "escalate_to_human",
                "add_to_cart",
                "remove_from_cart",
                "checkout_cart",
                "confirm_order",
            ],
        ),
    )
    assert updated_agent is not None
    assert updated_agent.name == "SQL Agent v2"
    assert updated_agent.status == "draft"
    assert updated_agent.version == 2
    assert updated_agent.business_profile == "Updated support desk profile."
    assert updated_agent.enabled_tools == [
        "escalate_to_human",
        "add_to_cart",
        "remove_from_cart",
        "checkout_cart",
        "confirm_order",
    ]

    republished_agent = repository.publish_agent(tenant.id, agent.id)
    assert republished_agent is not None
    assert republished_agent.status == "published"

    source = repository.create_knowledge_source(
        tenant.id,
        KnowledgeSourceCreateRequest(
            title="SQL FAQ",
            source_type="manual",
            content="Delivery takes 45 minutes and payment links expire after 10 minutes.",
        ),
    )
    assert source.status == "indexed"
    assert source.chunk_count == 1
    assert len(repository.list_ingestion_jobs(tenant.id)) == 1

    chat = repository.add_chat_message(
        tenant.id,
        ChatMessageRequest(
            agent_id=agent.id,
            channel="web_widget",
            message="How long does delivery take?",
        ),
    )
    assert chat.conversation.status == "resolved"
    assert chat.agent_message.confidence == 0.86
    assert "SQL FAQ" in chat.agent_message.content

    detail = repository.get_conversation_detail(tenant.id, chat.conversation.id)
    assert detail is not None
    _, messages, sources = detail
    assert [message.role for message in messages] == ["customer", "agent"]
    assert [source.title for source in sources] == ["SQL FAQ"]

    dashboard = repository.dashboard(tenant.id)
    assert dashboard is not None
    assert dashboard[1:] == (1, 1, 1, 0, 1.0)


def test_sqlalchemy_store_rotates_and_revokes_auth_sessions(sqlite_engine) -> None:
    create_schema(sqlite_engine)
    repository = SqlAlchemyStore(
        build_session_factory(sqlite_engine),
        Settings(database_url="sqlite+pysqlite:///:memory:"),
    )
    tenant, user, _ = repository.register(
        RegisterRequest(
            company_name="Session Tenant",
            owner_email="session@example.com",
            owner_name="Session Owner",
            password="safe-local-password",
        ),
        "test-secret",
    )
    session_id = uuid4()
    refresh_token, refresh_token_hash = issue_refresh_token(session_id, "test-secret")
    expires_at = datetime.now(UTC) + timedelta(days=30)
    repository.create_auth_session(session_id, tenant.id, user.id, refresh_token_hash, expires_at)

    refresh_claims = parse_refresh_token(refresh_token, "test-secret")
    new_session_id = uuid4()
    new_refresh_token, new_refresh_token_hash = issue_refresh_token(
        new_session_id,
        "test-secret",
    )
    rotated_session = repository.rotate_auth_session(
        refresh_claims.session_id,
        refresh_claims.token_hash,
        new_session_id,
        new_refresh_token_hash,
        datetime.now(UTC) + timedelta(days=30),
    )

    assert rotated_session is not None
    assert rotated_session.id == new_session_id
    assert (
        repository.rotate_auth_session(
            refresh_claims.session_id,
            refresh_claims.token_hash,
            uuid4(),
            new_refresh_token_hash,
            datetime.now(UTC) + timedelta(days=30),
        )
        is None
    )

    new_claims = parse_refresh_token(new_refresh_token, "test-secret")
    assert repository.revoke_auth_session(new_claims.session_id, new_claims.token_hash)
    assert not repository.revoke_auth_session(new_claims.session_id, new_claims.token_hash)


def test_fastapi_runtime_can_use_sqlalchemy_store(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'runtime.db'}"
    engine = build_engine(database_url)
    create_schema(engine)
    monkeypatch.setenv("STORE_BACKEND", "sqlalchemy")
    monkeypatch.setenv("DATABASE_URL", database_url)

    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.settings import get_settings
    from app.store_factory import get_app_store

    get_settings.cache_clear()
    get_app_store.cache_clear()
    client = TestClient(create_app())

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Runtime Tenant",
            "owner_email": "runtime@example.com",
            "owner_name": "Runtime Owner",
            "password": "safe-local-password",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant"]["id"]
    token = register_response.json()["access_token"]

    agent_response = client.post(
        "/api/v1/agents",
        headers={"Authorization": f"Bearer {token}", "x-tenant-id": tenant_id},
        json={
            "name": "Runtime Agent",
            "prompt": "Answer only from knowledge base and escalate otherwise.",
            "channel": "web_widget",
        },
    )
    assert agent_response.status_code == 201
    agents_response = client.get(
        "/api/v1/agents", headers={"Authorization": f"Bearer {token}", "x-tenant-id": tenant_id}
    )
    assert agents_response.json()[0]["name"] == "Runtime Agent"

    get_settings.cache_clear()
    get_app_store.cache_clear()
