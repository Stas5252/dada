from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, status
from pydantic import BaseModel

from app.contracts.outbound import Campaign, CampaignCreate, CampaignLead, CampaignLeadCreate
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=Campaign, status_code=status.HTTP_201_CREATED)
def create_campaign(
    campaign_in: CampaignCreate,
    tenant_id: UUID,
    store: AppStore = Depends(get_app_store),
) -> Campaign:
    return store.create_campaign(
        tenant_id=tenant_id,
        name=campaign_in.name,
        agent_id=campaign_in.agent_id,
        max_attempts=campaign_in.max_attempts,
        retry_delay_minutes=campaign_in.retry_delay_minutes,
    )


@router.get("", response_model=list[Campaign])
def list_campaigns(
    tenant_id: UUID,
    store: AppStore = Depends(get_app_store),
) -> list[Campaign]:
    return store.list_campaigns(tenant_id=tenant_id)


@router.get("/{campaign_id}", response_model=Campaign)
def get_campaign(
    campaign_id: str,
    tenant_id: UUID,
    store: AppStore = Depends(get_app_store),
) -> Campaign:
    campaign = store.get_campaign(tenant_id=tenant_id, campaign_id=campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


class StartCampaignRequest(BaseModel):
    status: str


@router.post("/{campaign_id}/start", response_model=Campaign)
def update_campaign_status(
    campaign_id: str,
    req: StartCampaignRequest,
    tenant_id: UUID,
    store: AppStore = Depends(get_app_store),
) -> Campaign:
    campaign = store.update_campaign_status(tenant_id=tenant_id, campaign_id=campaign_id, status=req.status)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


@router.post("/{campaign_id}/leads", response_model=list[CampaignLead], status_code=status.HTTP_201_CREATED)
def add_leads(
    campaign_id: str,
    leads_in: list[CampaignLeadCreate],
    tenant_id: UUID,
    store: AppStore = Depends(get_app_store),
) -> list[CampaignLead]:
    campaign = store.get_campaign(tenant_id=tenant_id, campaign_id=campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    leads_out = []
    for lead in leads_in:
        created_lead = store.add_campaign_lead(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            phone=lead.phone,
            variables=lead.variables,
        )
        leads_out.append(created_lead)
    return leads_out


@router.get("/{campaign_id}/leads", response_model=list[CampaignLead])
def list_campaign_leads(
    campaign_id: str,
    tenant_id: UUID,
    store: AppStore = Depends(get_app_store),
) -> list[CampaignLead]:
    return store.list_campaign_leads(tenant_id=tenant_id, campaign_id=campaign_id)


@router.post("/webhooks/twilio/status")
async def twilio_status_webhook(
    tenant_id: str,
    lead_id: str,
    CallStatus: str = Form(...),
    store: AppStore = Depends(get_app_store),
) -> dict[str, str]:
    """
    Twilio StatusCallback endpoint.
    Updates the campaign lead outcome based on the call status.
    """
    # CallStatus values: queued, initiated, ringing, in-progress, completed, busy, failed, no-answer, canceled
    status_mapping = {
        "completed": "completed",
        "busy": "failed",
        "failed": "failed",
        "no-answer": "failed",
        "canceled": "failed",
    }
    
    lead_status = status_mapping.get(CallStatus)
    if lead_status:
        store.update_campaign_lead(
            tenant_id=UUID(tenant_id),
            lead_id=lead_id,
            status=lead_status,
            outcome=CallStatus
        )
    return {"status": "ok"}
