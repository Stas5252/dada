from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.v1.dependencies import require_tenant_permission
from app.channel_diagnostics import build_channel_webhook_diagnostics
from app.channel_policy import CHANNEL_POLICIES_SETTINGS_KEY, channel_policies_from_settings
from app.guard_rails import GUARDRAIL_POLICY_SETTINGS_KEY, guardrail_policy_from_settings
from app.integration_readiness import build_integration_readiness
from app.rbac import Permission
from app.schemas import (
    ChannelPoliciesSettings,
    ChannelWebhookDiagnosticsResponse,
    DashboardResponse,
    GuardrailPolicySettings,
    IntegrationReadinessResponse,
    Tenant,
)
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/tenants", tags=["tenants"])
READ_DASHBOARD = require_tenant_permission(Permission.READ_CHAT)


@router.get("/{tenant_id}/dashboard", response_model=DashboardResponse)
async def dashboard(
    tenant_id: UUID,
    current_tenant_id: str = Depends(READ_DASHBOARD),
    app_store: AppStore = Depends(get_app_store),
) -> DashboardResponse:
    if str(tenant_id) != current_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant = app_store.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    agents = app_store.list_agents(tenant_id)
    sources = app_store.list_knowledge_sources(tenant_id)
    conversations = app_store.list_conversations(tenant_id)
    resolved = [
        conversation
        for conversation in conversations
        if conversation.resolution_status == "resolved"
    ]
    automation_rate = len(resolved) / len(conversations) if conversations else 0
    return DashboardResponse(
        tenant=tenant,
        agents_total=len(agents),
        knowledge_sources_total=len(sources),
        conversations_total=len(conversations),
        unresolved_topics_total=len(conversations) - len(resolved),
        automation_rate=automation_rate,
    )


class TenantSettingsUpdate(BaseModel):
    settings: dict[str, object]


MANAGE_TENANT = require_tenant_permission(Permission.MANAGE_CHAT)


def _get_owned_tenant(
    tenant_id: UUID,
    current_tenant_id: str,
    app_store: AppStore,
) -> Tenant:
    if str(tenant_id) != current_tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant = app_store.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.get("/{tenant_id}/settings")
async def get_tenant_settings(
    tenant_id: UUID,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, object]:
    tenant = _get_owned_tenant(tenant_id, current_tenant_id, app_store)
    return tenant.settings


@router.get(
    "/{tenant_id}/settings/integration-readiness",
    response_model=IntegrationReadinessResponse,
)
async def get_integration_readiness(
    tenant_id: UUID,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> IntegrationReadinessResponse:
    tenant = _get_owned_tenant(tenant_id, current_tenant_id, app_store)
    return build_integration_readiness(tenant.settings, settings)


@router.get(
    "/{tenant_id}/settings/channel-webhooks",
    response_model=ChannelWebhookDiagnosticsResponse,
)
async def get_channel_webhook_diagnostics(
    tenant_id: UUID,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
    settings: Settings = Depends(get_settings),
) -> ChannelWebhookDiagnosticsResponse:
    tenant = _get_owned_tenant(tenant_id, current_tenant_id, app_store)
    agents = app_store.list_agents(tenant_id)
    return build_channel_webhook_diagnostics(tenant, agents, settings)


@router.post("/{tenant_id}/settings")
async def update_tenant_settings_endpoint(
    tenant_id: UUID,
    payload: TenantSettingsUpdate,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, object]:
    _get_owned_tenant(tenant_id, current_tenant_id, app_store)
    updated = app_store.update_tenant_settings(tenant_id, payload.settings)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return updated.settings


@router.get(
    "/{tenant_id}/settings/guardrails",
    response_model=GuardrailPolicySettings,
)
async def get_guardrail_policy_settings(
    tenant_id: UUID,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
) -> GuardrailPolicySettings:
    tenant = _get_owned_tenant(tenant_id, current_tenant_id, app_store)
    return guardrail_policy_from_settings(tenant.settings)


@router.post(
    "/{tenant_id}/settings/guardrails",
    response_model=GuardrailPolicySettings,
)
async def update_guardrail_policy_settings(
    tenant_id: UUID,
    payload: GuardrailPolicySettings,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
) -> GuardrailPolicySettings:
    _get_owned_tenant(tenant_id, current_tenant_id, app_store)
    updated = app_store.update_tenant_settings(
        tenant_id,
        {GUARDRAIL_POLICY_SETTINGS_KEY: payload.model_dump()},
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    app_store.create_audit_log(
        tenant_id=tenant_id,
        user_id=None,
        event_type="tenant.guardrail_policy.updated",
        ip_address=None,
        details={
            "enabled": str(payload.enabled).lower(),
            "custom_regulated_terms": str(len(payload.custom_regulated_terms)),
            "custom_prohibited_claims": str(len(payload.custom_prohibited_claims)),
        },
    )
    return guardrail_policy_from_settings(updated.settings)


@router.get(
    "/{tenant_id}/settings/channel-policies",
    response_model=ChannelPoliciesSettings,
)
async def get_channel_policy_settings(
    tenant_id: UUID,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
) -> ChannelPoliciesSettings:
    tenant = _get_owned_tenant(tenant_id, current_tenant_id, app_store)
    return channel_policies_from_settings(tenant.settings)


@router.post(
    "/{tenant_id}/settings/channel-policies",
    response_model=ChannelPoliciesSettings,
)
async def update_channel_policy_settings(
    tenant_id: UUID,
    payload: ChannelPoliciesSettings,
    current_tenant_id: str = Depends(MANAGE_TENANT),
    app_store: AppStore = Depends(get_app_store),
) -> ChannelPoliciesSettings:
    _get_owned_tenant(tenant_id, current_tenant_id, app_store)
    updated = app_store.update_tenant_settings(
        tenant_id,
        {CHANNEL_POLICIES_SETTINGS_KEY: payload.model_dump(mode="json")},
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    app_store.create_audit_log(
        tenant_id=tenant_id,
        user_id=None,
        event_type="tenant.channel_policies.updated",
        ip_address=None,
        details={
            "telegram_mode": payload.telegram.mode.value,
            "vk_mode": payload.vk.mode.value,
            "whatsapp_mode": payload.whatsapp.mode.value,
            "web_widget_mode": payload.web_widget.mode.value,
            "voice_mode": payload.voice.mode.value,
        },
    )
    return channel_policies_from_settings(updated.settings)
