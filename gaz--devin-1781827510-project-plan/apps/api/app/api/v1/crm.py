import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict

from app.api.v1.dependencies import require_tenant_permission
from app.database import session_scope
from app.db_models import CrmDealModel, CrmLeadModel, CrmTaskModel
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


class DealStatusUpdate(BaseModel):
    status: str


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


class TaskResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    status: str
    due_date: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TaskStatusUpdate(BaseModel):
    status: str





def auto_create_lead(tenant_id: UUID, name: str, phone: str | None, email: str | None = None, source: str = "auto", app_store: Any = None) -> CrmLeadModel | None:
    """Helper for orchestrator/action_engine to automatically create a lead if missing."""
    if not phone and not email:
        return None
    from uuid import uuid4
    with app_store._session_scope() as session:
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
    app_store: Any = Depends(get_app_store),
) -> LeadResponse:
    from uuid import uuid4
    with app_store._session_scope() as session:
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
    app_store: Any = Depends(get_app_store),
) -> list[LeadResponse]:
    with app_store._session_scope() as session:
        leads = session.query(CrmLeadModel).filter(CrmLeadModel.tenant_id == tenant_id).order_by(CrmLeadModel.created_at.desc()).all()
        return [LeadResponse.model_validate(l) for l in leads]


@router.post("/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    payload: DealCreateRequest,
    tenant_id: str = Depends(MANAGE_CRM),
    app_store: Any = Depends(get_app_store),
) -> DealResponse:
    from uuid import uuid4
    with app_store._session_scope() as session:
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


@router.get("/deals", response_model=list[DealResponse])
def list_deals(
    tenant_id: str = Depends(READ_CRM),
    app_store: Any = Depends(get_app_store),
) -> list[DealResponse]:
    with app_store._session_scope() as session:
        deals = session.query(CrmDealModel).filter(CrmDealModel.tenant_id == tenant_id).order_by(CrmDealModel.created_at.desc()).all()
        return [DealResponse.model_validate(d) for d in deals]


@router.patch("/deals/{deal_id}/status", response_model=DealResponse)
def update_deal_status(
    deal_id: str,
    payload: DealStatusUpdate,
    tenant_id: str = Depends(MANAGE_CRM),
    app_store: Any = Depends(get_app_store),
) -> DealResponse:
    with app_store._session_scope() as session:
        deal = session.query(CrmDealModel).filter(CrmDealModel.tenant_id == tenant_id, CrmDealModel.id == deal_id).first()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        deal.status = payload.status
        session.flush()
        session.refresh(deal)
        return DealResponse.model_validate(deal)


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    tenant_id: str = Depends(READ_CRM),
    app_store: Any = Depends(get_app_store),
) -> list[TaskResponse]:
    with app_store._session_scope() as session:
        tasks = session.query(CrmTaskModel).filter(CrmTaskModel.tenant_id == tenant_id).order_by(CrmTaskModel.created_at.desc()).all()
        return [TaskResponse.model_validate(t) for t in tasks]


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
def update_task_status(
    task_id: str,
    payload: TaskStatusUpdate,
    tenant_id: str = Depends(MANAGE_CRM),
    app_store: Any = Depends(get_app_store),
) -> TaskResponse:
    with app_store._session_scope() as session:
        task = session.query(CrmTaskModel).filter(CrmTaskModel.tenant_id == tenant_id, CrmTaskModel.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task.status = payload.status
        session.flush()
        session.refresh(task)
        return TaskResponse.model_validate(task)


@router.get("/leads/export", response_class=PlainTextResponse)
def export_leads_csv(
    tenant_id: str = Depends(READ_CRM),
    app_store: Any = Depends(get_app_store),
) -> str:
    import io
    import csv
    with app_store._session_scope() as session:
        leads = session.query(CrmLeadModel).filter(CrmLeadModel.tenant_id == tenant_id).order_by(CrmLeadModel.created_at.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Name", "Phone", "Email", "Source", "Status", "Created At"])
        for lead in leads:
            writer.writerow([
                lead.id,
                lead.name,
                lead.phone or "",
                lead.email or "",
                lead.source or "",
                lead.status or "",
                lead.created_at.isoformat() if lead.created_at else "",
            ])
        
        return output.getvalue()
