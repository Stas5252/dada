from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from app.rbac import Permission, PermissionDeniedError, Role, assert_role_allowed
from app.schemas import Tenant, User
from app.security import AccessTokenClaims, AccessTokenError, verify_access_token
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store


@dataclass(frozen=True)
class AuthContext:
    tenant: Tenant
    user: User
    claims: AccessTokenClaims

    @property
    def tenant_id(self) -> str:
        return str(self.tenant.id)

    @property
    def user_id(self) -> str:
        return str(self.user.id)

    @property
    def role(self) -> Role:
        return self.user.role


async def require_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "TENANT_HEADER_REQUIRED",
                "message": "x-tenant-id header is required.",
            },
        )
    return x_tenant_id


def require_tenant_permission(permission: Permission) -> Callable[..., Awaitable[str]]:
    async def dependency(
        authorization: str | None = Header(default=None),
        x_tenant_id: str | None = Header(default=None),
        settings: Settings = Depends(get_settings),
        app_store: AppStore = Depends(get_app_store),
    ) -> str:
        token = _extract_optional_bearer_token(authorization)
        if token is None:
            raise _unauthorized("Bearer access token is required.")
        auth_context = _resolve_auth_context(
            token=token,
            x_tenant_id=x_tenant_id,
            settings=settings,
            app_store=app_store,
        )
        try:
            assert_role_allowed(auth_context.role, permission)
        except PermissionDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ROLE_PERMISSION_DENIED",
                    "message": "Current user role cannot perform this action.",
                },
            ) from exc
        return str(auth_context.tenant.id)

    return dependency


async def resolve_current_principal(
    authorization: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> AuthContext:
    token = _extract_bearer_token(authorization)
    return _resolve_auth_context(
        token=token,
        x_tenant_id=x_tenant_id,
        settings=settings,
        app_store=app_store,
    )


def _resolve_auth_context(
    *,
    token: str,
    x_tenant_id: str | None,
    settings: Settings,
    app_store: AppStore,
) -> AuthContext:
    try:
        claims = verify_access_token(token, settings.access_token_secret)
    except AccessTokenError as exc:
        raise _unauthorized("Invalid or expired access token.") from exc

    tenant = app_store.get_tenant(claims.tenant_id)
    user = app_store.get_user(claims.user_id)
    if tenant is None or user is None or user.tenant_id != tenant.id:
        raise _unauthorized("Invalid or expired access token.")
    if x_tenant_id is not None and x_tenant_id != str(claims.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "TENANT_TOKEN_MISMATCH",
                "message": "x-tenant-id does not match bearer token tenant.",
            },
        )
    return AuthContext(tenant=tenant, user=user, claims=claims)


def require_permission(permission: Permission) -> Callable[[AuthContext], Awaitable[AuthContext]]:
    async def dependency(
        auth_context: AuthContext = Depends(resolve_current_principal),
    ) -> AuthContext:
        try:
            assert_role_allowed(auth_context.role, permission)
        except PermissionDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ROLE_PERMISSION_DENIED",
                    "message": "Current user role cannot perform this action.",
                },
            ) from exc
        return auth_context

    return dependency


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise _unauthorized("Bearer access token is required.")
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token:
        raise _unauthorized("Bearer access token is required.")
    return token


def _extract_optional_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    return _extract_bearer_token(authorization)


def _resolve_legacy_tenant_id(x_tenant_id: str | None) -> str:
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "TENANT_HEADER_REQUIRED",
                "message": "x-tenant-id header is required.",
            },
        )
    return x_tenant_id


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error_code": "INVALID_ACCESS_TOKEN",
            "message": message,
        },
        headers={"WWW-Authenticate": "Bearer"},
    )

def check_billing_limit(tenant_id: UUID, app_store: AppStore) -> None:
    tenant = app_store.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    from datetime import UTC, datetime
    # Count only messages in the current calendar month
    since = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    messages_used = app_store.count_messages(tenant_id, since=since)
    limit_map = {
        "free": 100,
        "start": 1000,
        "pro": 10000,
        "enterprise": 999999,
    }
    limit = limit_map.get(tenant.plan.lower(), 1000)
    if messages_used >= limit:
        message = (
            f"Billing limit reached. Plan '{tenant.plan}' allows up to {limit} messages. "
            "Please upgrade."
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error_code": "BILLING_LIMIT_REACHED",
                "message": message,
            },
        )


def find_tenant_for_agent(agent_id: str, app_store: AppStore) -> str | None:
    """
    Find the tenant that owns a given agent.
    Works with both InMemoryStore and SqlAlchemyStore.
    """
    try:
        agent_uuid = UUID(agent_id)
    except ValueError:
        return None

    # For InMemoryStore: check agents dict directly
    if hasattr(app_store, "agents"):
        agent = app_store.agents.get(agent_uuid)
        if agent:
            return str(agent.tenant_id)

    # For SqlAlchemyStore: query database globally to resolve tenant
    if hasattr(app_store, "session_factory"):
        from app.db_models import AgentModel
        with app_store.session_factory() as session:
            agent_model = session.get(AgentModel, str(agent_uuid))
            if agent_model:
                return str(agent_model.tenant_id)

    # Fallback: try demo tenant
    from app.settings import get_settings

    settings = get_settings()
    agent = app_store.get_agent(UUID(settings.demo_tenant_id), agent_uuid)
    if agent:
        return settings.demo_tenant_id

    return None
