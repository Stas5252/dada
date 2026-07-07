import sentry_sdk
from fastapi import FastAPI, Request, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.agents import router as agents_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.crm import router as crm_router
from app.api.v1.health import router as health_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.voice import router as voice_router
from app.api.v1.campaigns import router as campaigns_router
from app.settings import get_settings
from app.tenant import TenantContextMiddleware


def _rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests, please try again later.",
        },
    )


def create_app() -> FastAPI:
    settings = get_settings()
    from app.logging_setup import setup_logging
    setup_logging(settings.app_env)

    cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

    # Security: block startup if default secret is used in production
    if (
        settings.app_env not in ("local", "test", "development")
        and settings.access_token_secret == "local-development-token-secret"  # nosec B105
    ):
        raise RuntimeError(
            "CRITICAL: ACCESS_TOKEN_SECRET is set to the insecure default. "
            "Set a strong, unique secret before deploying to production."
        )
    elif settings.access_token_secret == "local-development-token-secret":  # nosec B105
        import logging

        logging.getLogger(__name__).warning(
            "WARNING: ACCESS_TOKEN_SECRET is using the default insecure value. "
            "This is OK for local development, but MUST be changed for production."
        )

    if settings.sentry_dsn:
        is_prod = settings.app_env in ("production", "staging")
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.1 if is_prod else 1.0,
            profiles_sample_rate=0.1 if is_prod else 1.0,
            environment=settings.app_env,
        )

    import asyncio
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        task = None
        if settings.asterisk_ari_username and settings.asterisk_ari_password:
            from app.asterisk_ari_service import get_asterisk_ari_service
            ari_service = get_asterisk_ari_service()
            task = asyncio.create_task(ari_service.run())
            
        import urllib.parse
        from arq import create_pool
        from arq.connections import RedisSettings
        import app.store_factory as store_factory
        import sys
        
        pool = None
        if settings.app_env != "test" and "pytest" not in sys.modules:
            parsed = urllib.parse.urlparse(settings.redis_url)
            redis_settings = RedisSettings(
                host=parsed.hostname or 'localhost',
                port=parsed.port or 6379,
                database=int(parsed.path.lstrip('/')) if parsed.path and parsed.path != '/' else 0
            )
            pool = await create_pool(redis_settings)
            store_factory.GLOBAL_ARQ_POOL = pool
        
        yield
        
        if task is not None:
            task.cancel()
        if pool is not None:
            await pool.close()


    app = FastAPI(
        title="CallForce API",
        version=settings.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    from app.tracing import setup_tracing
    setup_tracing(app, settings)

    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    from app.limiter import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    from typing import Any, cast

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response

    class SecureHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Response:
            response = cast(Response, await call_next(request))
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            return response

    app.add_middleware(SecureHeadersMiddleware)

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(tenants_router, prefix="/api/v1")
    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(integrations_router, prefix="/api/v1")
    app.include_router(voice_router, prefix="/api/v1")
    app.include_router(campaigns_router, prefix="/api/v1")
    app.include_router(inbox_router, prefix="/api/v1/inbox")
    from app.api.v1.telegram import router as telegram_router

    app.include_router(telegram_router, prefix="/api/v1")
    app.include_router(billing_router, prefix="/api/v1")
    from app.api.v1.team import router as team_router

    app.include_router(team_router, prefix="/api/v1")
    from app.api.v1.analytics import router as analytics_router

    app.include_router(analytics_router, prefix="/api/v1")
    from app.api.v1.api_keys import router as api_keys_router

    app.include_router(api_keys_router, prefix="/api/v1")
    from app.api.v1.widget import router as widget_router
    app.include_router(widget_router, prefix="/api/v1")

    from app.api.v1.vk import router as vk_router
    app.include_router(vk_router, prefix="/api/v1")

    from app.api.v1.whatsapp import router as whatsapp_router
    app.include_router(whatsapp_router, prefix="/api/v1")
    from app.api.v1.avito import router as avito_router
    app.include_router(avito_router, prefix="/api/v1")
    from app.api.v1.meta import router as meta_router
    app.include_router(meta_router, prefix="/api/v1")
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api/v1")
    from app.api.v1.demo import router as demo_router
    app.include_router(demo_router, prefix="/api/v1")
    
    from app.api.v1.testbed import router as testbed_router
    app.include_router(testbed_router, prefix="/api/v1")

    from app.api.v1.admin import router as admin_router
    app.include_router(admin_router, prefix="/api/v1")
    
    app.include_router(crm_router, prefix="/api/v1")

    from app.api.v1.operator_ws import router as operator_ws_router
    app.include_router(operator_ws_router, prefix="/api/v1")

    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app, include_in_schema=False, should_gzip=True)

    return app


app = create_app()
