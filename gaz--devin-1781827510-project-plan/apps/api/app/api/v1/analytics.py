"""
Analytics API endpoints.
Provides dashboard metrics, agent performance, and unresolved topics.
"""

from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.v1.dependencies import AuthContext, require_permission
from app.rbac import Permission
from app.store_factory import AppStore, get_app_store
from app.schemas import WeeklyReport, QAEvaluation, QAEvaluationRequest, MarginDashboardResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])

READ_AUDIT = require_permission(Permission.READ_AUDIT)


class ChannelBreakdown(BaseModel):
    channel: str
    count: int


class DailyConversation(BaseModel):
    date: str
    count: int


class AgentStats(BaseModel):
    agent_id: str
    agent_name: str
    status: str
    total_conversations: int
    resolved: int
    escalated: int
    automation_rate: float


class UnresolvedTopic(BaseModel):
    question: str
    count: int
    last_seen: datetime


class AnalyticsOverview(BaseModel):
    total_conversations: int
    resolved: int
    escalated: int
    open: int
    automation_rate: float
    total_agents: int
    active_agents: int
    total_knowledge_sources: int
    total_messages: int
    avg_messages_per_conversation: float
    total_pipeline_value: float = 0.0
    estimated_lost_revenue: float = 0.0
    conversations_by_channel: list[ChannelBreakdown]
    conversations_by_day: list[DailyConversation]
    top_unresolved: list[UnresolvedTopic]


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    auth: AuthContext = Depends(READ_AUDIT),
    app_store: AppStore = Depends(get_app_store),
) -> AnalyticsOverview:
    """Get analytics overview for the current tenant."""
    tenant_id = UUID(auth.tenant_id)

    overview = app_store.get_analytics_overview(tenant_id)

    return AnalyticsOverview(
        total_conversations=overview["total_conversations"],
        resolved=overview["resolved"],
        escalated=overview["escalated"],
        open=overview["open"],
        automation_rate=round(overview["automation_rate"], 1),
        total_agents=overview["total_agents"],
        active_agents=overview["active_agents"],
        total_knowledge_sources=overview["total_knowledge_sources"],
        total_messages=overview["total_messages"],
        avg_messages_per_conversation=round(overview["avg_messages_per_conversation"], 1),
        total_pipeline_value=overview.get("total_pipeline_value", 0.0),
        estimated_lost_revenue=overview.get("estimated_lost_revenue", 0.0),
        conversations_by_channel=[ChannelBreakdown(**cb) for cb in overview["conversations_by_channel"]],
        conversations_by_day=[DailyConversation(**db) for db in overview["conversations_by_day"]],
        top_unresolved=[],
    )


@router.get("/agents", response_model=list[AgentStats])
async def analytics_agents(
    auth: AuthContext = Depends(READ_AUDIT),
    app_store: AppStore = Depends(get_app_store),
) -> list[AgentStats]:
    """Get per-agent statistics."""
    tenant_id = UUID(auth.tenant_id)

    agents = app_store.list_agents(tenant_id)
    conversations = app_store.list_conversations(tenant_id)

    result: list[AgentStats] = []
    for agent in agents:
        agent_convs = [c for c in conversations if c.agent_id == agent.id]
        total = len(agent_convs)
        resolved = sum(1 for c in agent_convs if c.status.value == "resolved")
        escalated = sum(1 for c in agent_convs if c.status.value == "escalated")
        rate = (resolved / total * 100) if total > 0 else 0.0

        result.append(
            AgentStats(
                agent_id=str(agent.id),
                agent_name=agent.name,
                status=agent.status.value,
                total_conversations=total,
                resolved=resolved,
                escalated=escalated,
                automation_rate=round(rate, 1),
            )
        )

    return result


@router.get("/reports", response_model=list[WeeklyReport])
async def list_weekly_reports(
    auth: AuthContext = Depends(READ_AUDIT),
    app_store: AppStore = Depends(get_app_store),
) -> list[WeeklyReport]:
    """Get list of weekly reports."""
    tenant_id = UUID(auth.tenant_id)
    return app_store.list_weekly_reports(tenant_id)


@router.get("/margin", response_model=MarginDashboardResponse)
async def get_margin_dashboard(
    auth: AuthContext = Depends(READ_AUDIT),
    app_store: AppStore = Depends(get_app_store),
) -> MarginDashboardResponse:
    """Get margin dashboard stats."""
    tenant_id = UUID(auth.tenant_id)
    data = app_store.get_margin_dashboard(tenant_id)
    return MarginDashboardResponse(**data)


@router.post("/evaluations", response_model=QAEvaluation, status_code=201)
async def create_qa_evaluation(
    payload: QAEvaluationRequest,
    auth: AuthContext = Depends(READ_AUDIT), # Ideally requires a WRITE_EVALUATION permission, but using READ_AUDIT for simplicity in Phase D
    app_store: AppStore = Depends(get_app_store),
) -> QAEvaluation:
    """Submit a QA evaluation (feedback loop) for a conversation."""
    tenant_id = UUID(auth.tenant_id)
    eval_model = QAEvaluation(
        tenant_id=tenant_id,
        conversation_id=payload.conversation_id,
        score=payload.score,
        flags=payload.flags,
        feedback=payload.feedback,
    )
    app_store.save_qa_evaluation(eval_model)
    return eval_model


class GenerateReportResponse(BaseModel):
    message: str
    job_id: str


@router.post("/reports/generate", response_model=GenerateReportResponse)
async def generate_report(
    auth: AuthContext = Depends(READ_AUDIT),
    app_store: AppStore = Depends(get_app_store),
) -> GenerateReportResponse:
    """Trigger background generation of weekly AI report."""
    from uuid import uuid4
    job_id = uuid4()
    app_store.background_jobs.submit(
        "run_weekly_report",
        job_id,
        tenant_id=auth.tenant_id,
        _store=app_store
    )
    return GenerateReportResponse(
        message="Отчет поставлен в очередь на генерацию.",
        job_id=str(job_id)
    )


@router.get("/conversations/{conversation_id}/qa", response_model=list[QAEvaluation])
async def get_conversation_qa(
    conversation_id: str,
    auth: AuthContext = Depends(READ_AUDIT),
    app_store: AppStore = Depends(get_app_store),
) -> list[QAEvaluation]:
    """Get QA evaluations for a conversation."""
    return app_store.get_qa_evaluations(UUID(auth.tenant_id), UUID(conversation_id))
