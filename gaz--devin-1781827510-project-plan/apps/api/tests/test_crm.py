import pytest
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from app.main import create_app
from app.contracts.action_engine import ToolInvocation
from app.action_engine_executor import ActionEngineExecutor
from app.store_factory import get_app_store

@pytest.fixture
def auth_client():
    client = TestClient(create_app())
    # Register test tenant
    email = f"crm_test_{uuid4().hex}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "CRM Test",
            "owner_email": email,
            "owner_name": "Owner",
            "password": "safe-password"
        }
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data["access_token"]
    tenant_id = data["tenant"]["id"]
    
    client.headers.update({
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id
    })
    return client, tenant_id

def test_crm_api_create_and_list_lead(auth_client):
    client, tenant_id = auth_client
    
    # Create lead
    resp = client.post("/api/v1/crm/leads", json={
        "name": "John Doe",
        "phone": "+1234567890",
        "email": "john@example.com",
        "source": "web"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "John Doe"
    assert data["phone"] == "+1234567890"
    lead_id = data["id"]
    
    # List leads
    resp = client.get("/api/v1/crm/leads")
    assert resp.status_code == 200
    leads = resp.json()
    assert len(leads) >= 1
    assert any(l["id"] == lead_id for l in leads)

def test_crm_api_create_deal(auth_client):
    client, tenant_id = auth_client
    
    resp = client.post("/api/v1/crm/deals", json={
        "title": "Big Enterprise Deal",
        "amount_minor": 15000000
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Big Enterprise Deal"
    assert data["amount_minor"] == 15000000

@pytest.mark.asyncio
async def test_action_engine_executor_crm_tools(auth_client):
    client, tenant_id = auth_client
    executor = ActionEngineExecutor()
    store = get_app_store()
    conv_id = uuid4()
    
    # Capture lead
    invocation1 = ToolInvocation(
        tenant_id=tenant_id,
        tool_name="capture_lead",
        input_payload={"name": "Alice AE", "phone": "+79998887766"},
        idempotency_key="key1"
    )
    res1 = await executor.execute_tool(UUID(tenant_id), conv_id, invocation1, store)
    assert res1["success"] is True
    assert "capture_lead" in res1["action_performed"]
    
    # Book appointment
    invocation2 = ToolInvocation(
        tenant_id=tenant_id,
        tool_name="book_appointment",
        input_payload={
            "service": "Consultation",
            "date": "2026-08-01",
            "time": "14:00",
            "customer_name": "Alice AE",
            "customer_phone": "+79998887766"
        },
        idempotency_key="key2"
    )
    res2 = await executor.execute_tool(UUID(tenant_id), conv_id, invocation2, store)
    assert res2["success"] is True
    assert "book_appointment" in res2["action_performed"]
    
    # Verify auto-created lead in API
    resp = client.get("/api/v1/crm/leads")
    leads = resp.json()
    alice_lead = next((l for l in leads if l["name"] == "Alice AE"), None)
    assert alice_lead is not None
    assert alice_lead["phone"] == "+79998887766"
