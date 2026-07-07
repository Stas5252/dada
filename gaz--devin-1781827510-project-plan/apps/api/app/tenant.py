from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.context import current_tenant_id
from app.settings import get_settings
from app.security import verify_access_token, AccessTokenError

class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        tenant_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.partition(" ")[2]
            try:
                settings = get_settings()
                claims = verify_access_token(token, settings.access_token_secret)
                tenant_id = str(claims.tenant_id)
            except AccessTokenError:
                pass
                
        request.state.tenant_id = tenant_id
        
        # Set contextvar for RLS
        token_ctx = current_tenant_id.set(tenant_id)
        try:
            return await call_next(request)
        finally:
            current_tenant_id.reset(token_ctx)
