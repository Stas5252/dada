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

    # Get all conversations
    conversations = app_store.list_conversations(tenant_id)
    agents = app_store.list_agents(tenant_id)
    sources = app_store.list_knowledge_sources(tenant_id)

    # Count by status
    resolved = sum(1 for c in conversations if c.status.value == "resolved")
    escalated = sum(1 for c in conversations if c.status.value == "escalated")
    open_count = sum(1 for c in conversations if c.status.value == "open")
    total = len(conversations)

    automation_rate = (resolved / total * 100) if total > 0 else 0.0

    # Count by channel
    channel_counts: Counter[str] = Counter()
    for c in conversations:
        channel_counts[c.channel] += 1
    channels = [ChannelBreakdown(channel=ch, count=cnt) for ch, cnt in channel_counts.most_common()]

    # Conversations by day (last 30 days)
    now = datetime.now(UTC)
    day_counts: Counter[str] = Counter()
    for c in conversations:
        day_str = c.created_at.strftime("%Y-%m-%d")
        day_counts[day_str] += 1

    # Fill in missing days
    daily: list[DailyConversation] = []
    for i in range(29, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        daily.append(DailyConversation(date=day, count=day_counts.get(day, 0)))

    # Count messages
    total_messages = app_store.count_messages(tenant_id)

    avg_msgs = (total_messages / total) if total > 0 else 0.0

    # Active agents (published)
    active_agents = sum(1 for a in agents if a.status.value == "published")

    # Unresolved topics (conversations marked as needs_human)
    unresolved: list[UnresolvedTopic] = []
    needs_human = [c for c in conversations if c.resolution_status == "needs_human"]
    topic_counter: Counter[str] = Counter()
    topic_last_seen: dict[str, datetime] = {}
    for c in needs_human:
        summary = c.summary[:80] if c.summary else "Без описания"
        topic_counter[summary] += 1
        if summary not in topic_last_seen or c.created_at > topic_last_seen[summary]:
            topic_last_seen[summary] = c.created_at

    for topic, count in topic_counter.most_common(10):
        unresolved.append(
            UnresolvedTopic(
                question=topic,
                count=count,
                last_seen=topic_last_seen[topic],
            )
        )

    return AnalyticsOverview(
        total_conversations=total,
        resolved=resolved,
        escalated=escalated,
        open=open_count,
        automation_rate=round(automation_rate, 1),
        total_agents=len(agents),
        active_agents=active_agents,
        total_knowledge_sources=len(sources),
        total_messages=total_messages,
        avg_messages_per_conversation=round(avg_msgs, 1),
        conversations_by_channel=channels,
        conversations_by_day=daily,
        top_unresolved=unresolved,
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
