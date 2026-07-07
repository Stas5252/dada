import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.store_factory import get_app_store

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def access_token(client: TestClient):
    import uuid
    uid = uuid.uuid4().hex[:8]
    res = client.post("/api/v1/auth/register", json={
        "company_name": f"Test Company {uid}",
        "owner_email": f"test_{uid}@example.com",
        "owner_name": "Test User",
        "password": "password123",
    })
    return res.json()["access_token"]

def test_analytics_overview(client: TestClient, access_token: str) -> None:
    res = client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "total_conversations" in data
    assert "automation_rate" in data

def test_list_reports(client: TestClient, access_token: str) -> None:
    res = client.get("/api/v1/analytics/reports", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_generate_report(client: TestClient, access_token: str) -> None:
    res = client.post("/api/v1/analytics/reports/generate", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert data["message"] == "Отчет поставлен в очередь на генерацию."

def test_get_conversation_qa(client: TestClient, access_token: str) -> None:
    from uuid import uuid4
    cid = str(uuid4())
    res = client.get(f"/api/v1/analytics/conversations/{cid}/qa", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)
