from contextvars import ContextVar

# Context variable to hold the current tenant_id (str) for RLS isolation
current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)
