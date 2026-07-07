from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.schemas import Tenant

BILLING_MONTHLY_MESSAGE_LIMIT_SETTING = "billing_monthly_message_limit"

PLAN_MONTHLY_MESSAGE_LIMITS = {
    "free": 100,
    "start": 1000,
    "pilot": 1000,
    "business": 5000,
    "pro": 10000,
    "enterprise": 999999,
}
DEFAULT_MONTHLY_MESSAGE_LIMIT = PLAN_MONTHLY_MESSAGE_LIMITS["start"]


class MessageUsageStore(Protocol):
    def count_messages(self, tenant_id: UUID, since: datetime | None = None) -> int: ...


@dataclass(frozen=True)
class BillingUsageSnapshot:
    plan: str
    period_start: datetime
    messages_used: int
    messages_limit: int
    messages_remaining: int
    limit_exceeded: bool


def billing_period_start(now: datetime | None = None) -> datetime:
    current = now or datetime.now(UTC)
    return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def resolve_monthly_message_limit(tenant: Tenant) -> int:
    custom_limit = tenant.settings.get(BILLING_MONTHLY_MESSAGE_LIMIT_SETTING)
    if isinstance(custom_limit, int) and not isinstance(custom_limit, bool) and custom_limit >= 0:
        return custom_limit
    if isinstance(custom_limit, str) and custom_limit.isdigit():
        return int(custom_limit)
    return PLAN_MONTHLY_MESSAGE_LIMITS.get(
        tenant.plan.casefold(),
        DEFAULT_MONTHLY_MESSAGE_LIMIT,
    )


def build_billing_usage_snapshot(
    tenant: Tenant,
    store: MessageUsageStore,
    now: datetime | None = None,
) -> BillingUsageSnapshot:
    period_start = billing_period_start(now)
    messages_used = store.count_messages(tenant.id, since=period_start)
    messages_limit = resolve_monthly_message_limit(tenant)
    messages_remaining = max(messages_limit - messages_used, 0)
    return BillingUsageSnapshot(
        plan=tenant.plan,
        period_start=period_start,
        messages_used=messages_used,
        messages_limit=messages_limit,
        messages_remaining=messages_remaining,
        limit_exceeded=messages_used >= messages_limit,
    )
