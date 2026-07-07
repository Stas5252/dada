from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import TestCaseStatus as CaseStatus
from app.store_factory import get_app_store


def _record_passing_testbed_run(tenant_id: str, agent_id: str, test_case_id: str) -> None:
    store = get_app_store()
    run = store.create_test_run(UUID(tenant_id), UUID(agent_id), UUID(test_case_id))
    updated_run = store.update_test_run(
        UUID(tenant_id),
        UUID(agent_id),
        run.id,
        CaseStatus.passed,
        logs=[
            {"role": "customer", "content": "Hello"},
            {"role": "agent", "content": "Hello, how can I help?"},
        ],
        result_summary="Expected outcome achieved.",
    )
    assert updated_run is not None


def test_core_mvp_chat_flow() -> None:
    client = TestClient(create_app())

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Pizza Demo",
            "owner_email": "owner@example.com",
            "owner_name": "Owner",
            "password": "safe-local-password",
        },
    )
    assert register_response.status_code == 201
    tenant_id = register_response.json()["tenant"]["id"]
    headers = {"x-tenant-id": tenant_id}

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "safe-local-password"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["tenant"]["id"] == tenant_id
    assert len(login_response.json()["access_token"].split(".")) == 3
    assert login_response.json()["refresh_token"].startswith("gaz-refresh.")

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "x-tenant-id": tenant_id}

    agent_response = client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "name": "Pizza operator",
            "prompt": "Answer only from knowledge and escalate when confidence is low.",
            "channel": "telegram",
        },
    )
    assert agent_response.status_code == 201
    agent_id = agent_response.json()["id"]

    blocked_publish_response = client.post(f"/api/v1/agents/{agent_id}/publish", headers=headers)
    assert blocked_publish_response.status_code == 409
    blocked_detail = blocked_publish_response.json()["detail"]
    assert blocked_detail["error_code"] == "TESTBED_PUBLISH_GATE_FAILED"
    assert blocked_detail["failures"][0]["code"] == "no_test_cases"

    test_case_response = client.post(
        f"/api/v1/agents/{agent_id}/testbed/cases",
        headers=headers,
        json={
            "name": "Pizza greeting",
            "scenario": "Customer asks for pizza delivery help.",
            "expected_outcome": "Agent greets the customer and offers delivery help.",
        },
    )
    assert test_case_response.status_code == 201
    test_case_id = test_case_response.json()["id"]

    missing_run_response = client.post(f"/api/v1/agents/{agent_id}/publish", headers=headers)
    assert missing_run_response.status_code == 409
    assert missing_run_response.json()["detail"]["failures"][0]["code"] == "missing_run"

    _record_passing_testbed_run(tenant_id, agent_id, test_case_id)

    publish_response = client.post(f"/api/v1/agents/{agent_id}/publish", headers=headers)
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"

    get_agent_response = client.get(f"/api/v1/agents/{agent_id}", headers=headers)
    assert get_agent_response.status_code == 200
    assert get_agent_response.json()["name"] == "Pizza operator"

    update_response = client.patch(
        f"/api/v1/agents/{agent_id}",
        headers=headers,
        json={
            "name": "Pizza support owner",
            "prompt": (
                "Answer from approved restaurant knowledge and escalate when confidence is low."
            ),
            "channel": "web_widget",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Pizza support owner"
    assert update_response.json()["channel"] == "web_widget"
    assert update_response.json()["status"] == "draft"
    assert update_response.json()["version"] == 2

    stale_publish_response = client.post(f"/api/v1/agents/{agent_id}/publish", headers=headers)
    assert stale_publish_response.status_code == 409
    assert stale_publish_response.json()["detail"]["failures"][0]["code"] == "stale_run"

    _record_passing_testbed_run(tenant_id, agent_id, test_case_id)

    republish_response = client.post(f"/api/v1/agents/{agent_id}/publish", headers=headers)
    assert republish_response.status_code == 200
    assert republish_response.json()["status"] == "published"

    source_response = client.post(
        "/api/v1/knowledge/sources",
        headers=headers,
        json={
            "title": "Delivery FAQ",
            "source_type": "manual",
            "content": "Доставка пиццы занимает 45 минут. Бесплатная доставка от 1000 рублей.",
        },
    )
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    ingest_response = client.post(
        f"/api/v1/knowledge/sources/{source_id}/ingest",
        headers=headers,
    )
    assert ingest_response.status_code == 202

    chat_response = client.post(
        "/api/v1/chat/mock",
        headers=headers,
        json={
            "agent_id": agent_id,
            "channel": "web_widget",
            "message": "Сколько занимает доставка пиццы?",
        },
    )
    assert chat_response.status_code == 201
    chat_payload = chat_response.json()
    print("CORE MVP CHAT PAYLOAD:", chat_payload)
    assert chat_payload["conversation"]["resolution_status"] == "resolved"
    assert chat_payload["agent_message"]["source_ids"]
    assert "Delivery FAQ" in chat_payload["agent_message"]["content"]

    conversations_response = client.get("/api/v1/conversations", headers=headers)
    assert conversations_response.status_code == 200
    assert len(conversations_response.json()) == 1

    dashboard_response = client.get(f"/api/v1/tenants/{tenant_id}/dashboard", headers=headers)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["agents_total"] == 1
    assert dashboard["knowledge_sources_total"] == 1
    assert dashboard["conversations_total"] == 1
    assert dashboard["automation_rate"] == 1


def test_knowledge_upload_and_ingestion_jobs_flow() -> None:
    client = TestClient(create_app())

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Knowledge Tenant",
            "owner_email": "knowledge@example.com",
            "owner_name": "Knowledge Owner",
            "password": "safe-local-password",
        },
    )
    assert register_response.status_code == 201
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    empty_upload_response = client.post(
        "/api/v1/knowledge/upload",
        headers=headers,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty_upload_response.status_code == 400

    upload_response = client.post(
        "/api/v1/knowledge/upload",
        headers=headers,
        files={
            "file": (
                "delivery.md",
                b"Delivery takes 45 minutes. Free delivery starts from 1000 RUB.",
                "text/markdown",
            )
        },
    )
    assert upload_response.status_code == 201
    source = upload_response.json()
    assert source["title"] == "delivery.md"
    assert source["status"] == "indexed"
    assert source["chunk_count"] == 1

    jobs_response = client.get("/api/v1/knowledge/ingestion/jobs", headers=headers)
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert len(jobs) == 1
    assert jobs[0]["source_id"] == source["id"]
    assert jobs[0]["status"] == "completed"

    replay_response = client.post(
        f"/api/v1/knowledge/sources/{source['id']}/ingest",
        headers=headers,
    )
    assert replay_response.status_code == 202
    assert replay_response.json()["id"] == jobs[0]["id"]


def test_tenant_isolation_blocks_dashboard_cross_access() -> None:
    client = TestClient(create_app())
    first = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "First Tenant",
            "owner_email": "first@example.com",
            "owner_name": "First Owner",
            "password": "safe-local-password",
        },
    )
    second = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Second Tenant",
            "owner_email": "second@example.com",
            "owner_name": "Second Owner",
            "password": "safe-local-password",
        },
    )
    first_tenant_id = first.json()["tenant"]["id"]
    second_tenant_id = second.json()["tenant"]["id"]
    second_token = second.json()["access_token"]

    response = client.get(
        f"/api/v1/tenants/{first_tenant_id}/dashboard",
        headers={"Authorization": f"Bearer {second_token}", "x-tenant-id": second_tenant_id},
    )

    assert response.status_code == 404


def test_invalid_login_is_rejected() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Security Tenant",
            "owner_email": "security@example.com",
            "owner_name": "Security Owner",
            "password": "safe-local-password",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "security@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
