from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


from app.context import current_tenant_id

class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        tenant_id = request.headers.get("x-tenant-id")
        request.state.tenant_id = tenant_id
        
        # Set contextvar for RLS
        token = current_tenant_id.set(tenant_id)
        try:
            return await call_next(request)
        finally:
            current_tenant_id.reset(token)
