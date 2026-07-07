import pytest
from uuid import uuid4, UUID
from fastapi.testclient import TestClient

from app.contracts.outbound import CampaignCreate, CampaignLeadCreate
from app.worker import DISPATCH_CAMPAIGNS, DIAL_LEAD
from app.main import create_app
from app.store_factory import get_app_store
from app.demo_data import build_demo_tenant, build_demo_owner

@pytest.mark.asyncio
async def test_campaign_crud_and_leads():
    app = create_app()
    client = TestClient(app)
    app_store = get_app_store()
    
    tenant_id = UUID(int=0)
    agent_id = str(uuid4())
    
    # 1. Create Campaign
    create_req = {
        "name": "Test Campaign",
        "agent_id": agent_id,
        "max_attempts": 3,
        "retry_delay_minutes": 60
    }
    response = client.post(f"/api/v1/campaigns?tenant_id={tenant_id}", json=create_req)
    assert response.status_code == 201
    campaign = response.json()
    assert campaign["name"] == "Test Campaign"
    assert campaign["status"] == "draft"

    # 2. Add Leads
    leads_req = [
        {"phone": "+15551234567", "variables": {"name": "Alice"}},
        {"phone": "+15559876543", "variables": {"name": "Bob"}}
    ]
    response = client.post(f"/api/v1/campaigns/{campaign['id']}/leads?tenant_id={tenant_id}", json=leads_req)
    assert response.status_code == 201
    leads = response.json()
    assert len(leads) == 2
    assert leads[0]["phone"] == "+15551234567"
    assert leads[0]["status"] == "pending"

    # 3. Update Campaign Status to active
    response = client.post(f"/api/v1/campaigns/{campaign['id']}/start?tenant_id={tenant_id}", json={"status": "active"})
    assert response.status_code == 200
    assert response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_worker_dispatch_campaigns():
    app_store = get_app_store()
    tenant_id = UUID(int=0)
    agent_id = str(uuid4())
    
    # Setup active campaign and pending leads
    campaign = app_store.create_campaign(tenant_id, "Worker Test", agent_id, 3, 60)
    app_store.update_campaign_status(tenant_id, campaign.id, "active")
    
    lead1 = app_store.add_campaign_lead(tenant_id, campaign.id, "+15550001111", {})
    lead2 = app_store.add_campaign_lead(tenant_id, campaign.id, "+15550002222", {})
    
    class MockRedis:
        def __init__(self):
            self.enqueued = []
        async def enqueue_job(self, name, *args):
            self.enqueued.append((name, args))

    ctx = {"redis": MockRedis()}
    
    await DISPATCH_CAMPAIGNS(ctx)
    
    # Expect our 2 leads to be dispatched (there may be more from previous tests)
    enqueued_lead_ids = [args[1] for name, args in ctx["redis"].enqueued if name == "DIAL_LEAD"]
    assert lead1.id in enqueued_lead_ids
    assert lead2.id in enqueued_lead_ids

    # Test DIAL_LEAD simulation
    await DIAL_LEAD(ctx, str(tenant_id), lead1.id)
    
    # Lead should be marked dialing
    leads = app_store.list_campaign_leads(tenant_id, campaign.id)
    dialing_lead = next(l for l in leads if l.id == lead1.id)
    assert dialing_lead.status == "dialing" # Simulation Mode returns success and doesn't raise exception
    assert dialing_lead.attempts == 1
