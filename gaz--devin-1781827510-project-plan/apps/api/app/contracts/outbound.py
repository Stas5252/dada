from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class Campaign(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str
    name: str
    status: str
    max_attempts: int = Field(ge=1)
    retry_delay_minutes: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    name: str
    agent_id: str
    max_attempts: int = Field(default=1, ge=1)
    retry_delay_minutes: int = Field(default=60, ge=1)


class CampaignLead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    campaign_id: str
    phone: str
    variables: dict[str, Any]
    status: str
    attempts: int
    last_attempt_at: datetime | None
    outcome: str | None


class CampaignLeadCreate(BaseModel):
    phone: str
    variables: dict[str, Any] = Field(default_factory=dict)
