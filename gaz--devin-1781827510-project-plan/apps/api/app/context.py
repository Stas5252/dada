from contextvars import ContextVar
import contextlib
from collections.abc import Generator

# Context variable to hold the current tenant_id (str) for RLS isolation
current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)

@contextlib.contextmanager
def set_rls_tenant(tenant_id: str) -> Generator[None, None, None]:
    token = current_tenant_id.set(tenant_id)
    try:
        yield
    finally:
        current_tenant_id.reset(token)
