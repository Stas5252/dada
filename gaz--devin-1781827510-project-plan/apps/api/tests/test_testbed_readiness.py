from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas import TestCaseStatus as CaseStatus
from app.store_factory import get_app_store


def _register_agent(client: TestClient) -> tuple[dict[str, str], str, str]:
    email = f"testbed_ready_{uuid4().hex}@example.com"
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Testbed Ready Co",
            "owner_email": email,
            "owner_name": "Owner",
            "password": "safe-local-password",
        },
    )
    assert register_response.status_code == 201
    payload = register_response.json()
    tenant_id = payload["tenant"]["id"]
    headers = {"Authorization": f"Bearer {payload['access_token']}", "x-tenant-id": tenant_id}

    agent_response = client.post(
        "/api/v1/agents",
        headers=headers,
        json={
            "name": "Readiness Agent",
            "prompt": "Answer from the approved scenario and escalate unclear requests.",
            "channel": "web_widget",
        },
    )
    assert agent_response.status_code == 201
    return headers, tenant_id, agent_response.json()["id"]


def _create_case(client: TestClient, headers: dict[str, str], agent_id: str, name: str) -> str:
    response = client.post(
        f"/api/v1/agents/{agent_id}/testbed/cases",
        headers=headers,
        json={
            "name": name,
            "scenario": f"Customer asks for help in {name}.",
            "expected_outcome": "Agent answers clearly and follows policy.",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _record_run(tenant_id: str, agent_id: str, test_case_id: str, status: CaseStatus) -> None:
    store = get_app_store()
    run = store.create_test_run(UUID(tenant_id), UUID(agent_id), UUID(test_case_id))
    updated_run = store.update_test_run(
        UUID(tenant_id),
        UUID(agent_id),
        run.id,
        status,
        logs=[
            {"role": "customer", "content": "Hello"},
            {"role": "agent", "content": "Hello, how can I help?"},
        ],
        result_summary=f"Scenario {status.value}.",
    )
    assert updated_run is not None


def test_testbed_readiness_reports_quality_threshold_and_latest_runs() -> None:
    client = TestClient(create_app())
    headers, tenant_id, agent_id = _register_agent(client)

    empty_response = client.get(f"/api/v1/agents/{agent_id}/testbed/readiness", headers=headers)
    assert empty_response.status_code == 200
    empty_payload = empty_response.json()
    assert empty_payload["status"] == "action_required"
    assert empty_payload["publish_blocked"] is True
    assert empty_payload["minimum_test_cases"] == 1
    assert empty_payload["pass_rate"] == 0
    assert empty_payload["failures"][0]["code"] == "no_test_cases"

    passing_case_id = _create_case(client, headers, agent_id, "Greeting")
    failing_case_id = _create_case(client, headers, agent_id, "Escalation")
    _record_run(tenant_id, agent_id, passing_case_id, CaseStatus.passed)
    _record_run(tenant_id, agent_id, failing_case_id, CaseStatus.failed)

    partial_response = client.get(f"/api/v1/agents/{agent_id}/testbed/readiness", headers=headers)
    assert partial_response.status_code == 200
    partial_payload = partial_response.json()
    assert partial_payload["status"] == "action_required"
    assert partial_payload["publish_blocked"] is True
    assert partial_payload["total_cases"] == 2
    assert partial_payload["passing_cases"] == 1
    assert partial_payload["failing_cases"] == 1
    assert partial_payload["pass_rate"] == 0.5
    assert partial_payload["required_pass_rate"] == 1
    assert {case["status"] for case in partial_payload["cases"]} == {"passed", "failed"}

    blocked_publish_response = client.post(f"/api/v1/agents/{agent_id}/publish", headers=headers)
    assert blocked_publish_response.status_code == 409
    blocked_detail = blocked_publish_response.json()["detail"]
    assert blocked_detail["pass_rate"] == 0.5
    assert blocked_detail["required_pass_rate"] == 1
    assert blocked_detail["failures"][0]["code"] == "latest_run_failed"

    _record_run(tenant_id, agent_id, failing_case_id, CaseStatus.passed)

    ready_response = client.get(f"/api/v1/agents/{agent_id}/testbed/readiness", headers=headers)
    assert ready_response.status_code == 200
    ready_payload = ready_response.json()
    assert ready_payload["status"] == "ready"
    assert ready_payload["publish_blocked"] is False
    assert ready_payload["passing_cases"] == 2
    assert ready_payload["pass_rate"] == 1
    assert ready_payload["failures"] == []
