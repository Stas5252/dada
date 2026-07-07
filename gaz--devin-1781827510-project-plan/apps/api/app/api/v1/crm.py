import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.v1.dependencies import require_tenant_permission
from app.database import session_scope
from app.db_models import CrmDealModel, CrmLeadModel
from app.rbac import Permission
from app.settings import get_settings

router = APIRouter(prefix="/crm", tags=["crm"])
logger = logging.getLogger(__name__)

READ_CRM = require_tenant_permission(Permission.READ_CHAT)
MANAGE_CRM = require_tenant_permission(Permission.MANAGE_CHAT)


class LeadCreateRequest(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    source: str = "manual"
    status: str = "new"
    notes: str | None = None


class LeadResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    phone: str | None
    email: str | None
    source: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DealCreateRequest(BaseModel):
    lead_id: str | None = None
    title: str
    amount_minor: int = 0
    currency: str = "RUB"
    status: str = "open"


class DealResponse(BaseModel):
    id: str
    tenant_id: str
    lead_id: str | None
    title: str
    amount_minor: int
    currency: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


def get_db_session_factory():
    from app.database import build_engine, build_session_factory
    settings = get_settings()
    engine = build_engine(settings.database_url)
    return build_session_factory(engine)


def auto_create_lead(tenant_id: UUID, name: str, phone: str | None, email: str | None = None, source: str = "auto") -> CrmLeadModel | None:
    """Helper for orchestrator/action_engine to automatically create a lead if missing."""
    if not phone and not email:
        return None
    from uuid import uuid4
    factory = get_db_session_factory()
    with session_scope(factory) as session:
        # Check if exists
        query = session.query(CrmLeadModel).filter(CrmLeadModel.tenant_id == str(tenant_id))
        if phone:
            existing = query.filter(CrmLeadModel.phone == phone).first()
        else:
            existing = query.filter(CrmLeadModel.email == email).first()

        if existing:
            return existing

        lead = CrmLeadModel(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            name=name or "Unknown Customer",
            phone=phone,
            email=email,
            source=source,
            status="new",
        )
        session.add(lead)
        session.flush()
        session.refresh(lead)
        # Detach from session to return safely
        session.expunge(lead)
        return lead


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreateRequest,
    tenant_id: str = Depends(MANAGE_CRM),
) -> LeadResponse:
    from uuid import uuid4
    factory = get_db_session_factory()
    with session_scope(factory) as session:
        lead = CrmLeadModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            source=payload.source,
            status=payload.status,
        )
        session.add(lead)
        session.flush()
        session.refresh(lead)
        return LeadResponse.model_validate(lead)


@router.get("/leads", response_model=list[LeadResponse])
def list_leads(
    tenant_id: str = Depends(READ_CRM),
) -> list[LeadResponse]:
    factory = get_db_session_factory()
    with session_scope(factory) as session:
        leads = session.query(CrmLeadModel).filter(CrmLeadModel.tenant_id == tenant_id).order_by(CrmLeadModel.created_at.desc()).all()
        return [LeadResponse.model_validate(l) for l in leads]


@router.post("/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    payload: DealCreateRequest,
    tenant_id: str = Depends(MANAGE_CRM),
) -> DealResponse:
    from uuid import uuid4
    factory = get_db_session_factory()
    with session_scope(factory) as session:
        deal = CrmDealModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            lead_id=payload.lead_id,
            title=payload.title,
            amount_minor=payload.amount_minor,
            currency=payload.currency,
            status=payload.status,
            source="api",
        )
        session.add(deal)
        session.flush()
        session.refresh(deal)
        return DealResponse.model_validate(deal)
