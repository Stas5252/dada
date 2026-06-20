"""
API Keys management endpoints.
Allows tenants to create, list, and revoke API keys for programmatic access.
"""

import secrets
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import AuthContext, require_permission
from app.rbac import Permission
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

MANAGE_AUTH = require_permission(Permission.MANAGE_AUTH)
READ_AUTH = require_permission(Permission.READ_AUTH)


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scopes: list[str] = Field(default_factory=lambda: ["read", "write"])


class CreateApiKeyResponse(BaseModel):
    id: str
    name: str
    key: str  # Full key, shown ONLY on creation
    key_prefix: str
    scopes: list[str]
    created_at: datetime
    message: str


class ApiKeyListItem(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None
    revoked: bool


def _hash_key(key: str) -> str:
    import hashlib

    return hashlib.sha256(key.encode()).hexdigest()


@router.get("", response_model=list[ApiKeyListItem])
async def list_api_keys(
    auth: AuthContext = Depends(READ_AUTH),
    app_store: AppStore = Depends(get_app_store),
) -> list[ApiKeyListItem]:
    """List all API keys for the current tenant."""
    tenant_id = UUID(auth.tenant_id)
    keys = app_store.list_api_keys(tenant_id)

    return [
        ApiKeyListItem(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            revoked=k.revoked_at is not None,
        )
        for k in sorted(keys, key=lambda k: k.created_at, reverse=True)
    ]


@router.post("", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: CreateApiKeyRequest,
    auth: AuthContext = Depends(MANAGE_AUTH),
    app_store: AppStore = Depends(get_app_store),
) -> CreateApiKeyResponse:
    """Create a new API key. The full key is shown only once."""
    tenant_id = UUID(auth.tenant_id)

    # Generate key: cf_live_<random>
    raw_key = f"cf_live_{secrets.token_urlsafe(32)}"
    key_prefix = raw_key[:12] + "..."

    record = app_store.create_api_key(
        tenant_id=tenant_id,
        name=payload.name,
        key_prefix=key_prefix,
        key_hash=_hash_key(raw_key),
        created_by=auth.user.id,
        scopes=payload.scopes,
    )

    # Audit log
    app_store.create_audit_log(
        event_type="api_key.created",
        user_id=auth.user.id,
        tenant_id=tenant_id,
        details={"key_name": payload.name, "key_id": str(record.id)},
    )

    return CreateApiKeyResponse(
        id=str(record.id),
        name=record.name,
        key=raw_key,
        key_prefix=key_prefix,
        scopes=record.scopes,
        created_at=record.created_at,
        message="Сохраните ключ — он показывается только один раз.",
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    auth: AuthContext = Depends(MANAGE_AUTH),
    app_store: AppStore = Depends(get_app_store),
) -> None:
    """Revoke an API key."""
    tenant_id = UUID(auth.tenant_id)

    if app_store.revoke_api_key(tenant_id, key_id):
        app_store.create_audit_log(
            event_type="api_key.revoked",
            user_id=auth.user.id,
            tenant_id=tenant_id,
            details={"key_id": str(key_id)},
        )
        return

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
