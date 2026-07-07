from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from app.schemas import (
    Agent,
    AgentStatus,
    ChannelWebhookDiagnosticItem,
    ChannelWebhookDiagnosticsResponse,
    ChannelWebhookDiagnosticStatus,
    ChannelWebhookPublicUrlStatus,
    Tenant,
)
from app.settings import Settings


def build_channel_webhook_diagnostics(
    tenant: Tenant,
    agents: Sequence[Agent],
    settings: Settings,
) -> ChannelWebhookDiagnosticsResponse:
    public_base_url = _normalize_base_url(settings.api_public_url)
    public_url_status = _public_url_status(public_base_url)
    items = [
        _telegram_diagnostic(
            tenant=tenant,
            agents=agents,
            public_base_url=public_base_url,
            public_url_status=public_url_status,
        ),
        _vk_diagnostic(
            tenant=tenant,
            public_base_url=public_base_url,
            public_url_status=public_url_status,
        ),
        _whatsapp_diagnostic(
            tenant=tenant,
            public_base_url=public_base_url,
            public_url_status=public_url_status,
        ),
    ]
    return ChannelWebhookDiagnosticsResponse(
        checked_at=datetime.now(UTC),
        public_base_url=public_base_url,
        public_url_status=public_url_status,
        items=items,
    )


def _telegram_diagnostic(
    *,
    tenant: Tenant,
    agents: Sequence[Agent],
    public_base_url: str,
    public_url_status: ChannelWebhookPublicUrlStatus,
) -> ChannelWebhookDiagnosticItem:
    telegram_agents = [agent for agent in agents if agent.channel == "telegram"]
    connected_agent = next((agent for agent in telegram_agents if agent.telegram_bot_token), None)
    agent = connected_agent or (telegram_agents[0] if telegram_agents else None)
    webhook_url = f"{public_base_url}/api/v1/webhooks/telegram/{agent.id if agent else '{agent_id}'}"
    configured_settings: list[str] = []
    missing_settings: list[str] = []
    warnings = _public_url_warnings(public_url_status)

    if agent and agent.status == AgentStatus.published:
        configured_settings.append("published_telegram_agent")
    else:
        missing_settings.append("published_telegram_agent")
    if agent and agent.telegram_bot_token:
        configured_settings.append("agent.telegram_bot_token")
    else:
        missing_settings.append("agent.telegram_bot_token")
    if public_url_status == ChannelWebhookPublicUrlStatus.https_ready:
        configured_settings.append("API_PUBLIC_URL")
    else:
        missing_settings.append("API_PUBLIC_URL_HTTPS")

    ready = not missing_settings
    return ChannelWebhookDiagnosticItem(
        key="telegram",
        label="Telegram Bot API",
        provider="telegram",
        status=(
            ChannelWebhookDiagnosticStatus.ready
            if ready
            else ChannelWebhookDiagnosticStatus.needs_setup
        ),
        summary=(
            "Telegram webhook can be registered for the connected published agent."
            if ready
            else "Telegram needs a published connected agent and a public HTTPS API URL."
        ),
        inbound_webhook_url=webhook_url,
        required_settings=["published_telegram_agent", "agent.telegram_bot_token", "API_PUBLIC_URL"],
        configured_settings=configured_settings,
        missing_settings=missing_settings,
        setup_steps=[
            "Create or select a Telegram agent.",
            "Connect the bot token from BotFather on the agent page.",
            "Publish the agent after Testbed checks pass.",
            "Use the webhook URL shown here if manual provider setup is required.",
        ],
        security_notes=[
            "The connect flow registers Telegram setWebhook with x-telegram-bot-api-secret-token.",
            "Secret token value is derived from the bot token and is never returned by diagnostics.",
        ],
        warnings=warnings,
        setup_url="/agents",
        docs_url="/docs#telegram",
        test_mode=not ready,
    )


def _vk_diagnostic(
    *,
    tenant: Tenant,
    public_base_url: str,
    public_url_status: ChannelWebhookPublicUrlStatus,
) -> ChannelWebhookDiagnosticItem:
    tenant_settings = tenant.settings
    webhook_url = f"{public_base_url}/api/v1/webhooks/vk/{tenant.id}"
    required_settings = ["vk_group_token", "vk_confirmation_code", "API_PUBLIC_URL"]
    configured_settings, missing_settings = _tenant_setting_state(
        tenant_settings,
        ["vk_group_token", "vk_confirmation_code"],
    )
    warnings = _public_url_warnings(public_url_status)
    if _has_value(tenant_settings.get("vk_secret_key")):
        configured_settings.append("vk_secret_key")
    else:
        warnings.append("Set vk_secret_key to reject spoofed VK callbacks.")
    if public_url_status == ChannelWebhookPublicUrlStatus.https_ready:
        configured_settings.append("API_PUBLIC_URL")
    else:
        missing_settings.append("API_PUBLIC_URL_HTTPS")

    if missing_settings:
        status = ChannelWebhookDiagnosticStatus.needs_setup
    elif warnings:
        status = ChannelWebhookDiagnosticStatus.warning
    else:
        status = ChannelWebhookDiagnosticStatus.ready

    return ChannelWebhookDiagnosticItem(
        key="vk",
        label="VK Communities",
        provider="vk",
        status=status,
        summary=(
            "VK webhook URL and confirmation code are ready."
            if status == ChannelWebhookDiagnosticStatus.ready
            else "VK requires a group token, confirmation code and public HTTPS callback URL."
        ),
        inbound_webhook_url=webhook_url,
        required_settings=[*required_settings, "vk_secret_key"],
        configured_settings=configured_settings,
        missing_settings=missing_settings,
        setup_steps=[
            "Open VK community callback API settings.",
            "Paste the webhook URL as the server address.",
            "Paste vk_confirmation_code as the confirmation string.",
            "Enable message_new events and set vk_secret_key for signed callbacks.",
        ],
        security_notes=[
            "If vk_secret_key is configured, incoming callbacks must include the matching secret.",
            "Diagnostics never return the token, confirmation code or secret value.",
        ],
        warnings=warnings,
        setup_url="/settings/channels#vk",
        docs_url="/docs#vk",
        test_mode=status != ChannelWebhookDiagnosticStatus.ready,
    )


def _whatsapp_diagnostic(
    *,
    tenant: Tenant,
    public_base_url: str,
    public_url_status: ChannelWebhookPublicUrlStatus,
) -> ChannelWebhookDiagnosticItem:
    tenant_settings = tenant.settings
    webhook_url = f"{public_base_url}/api/v1/webhooks/whatsapp/{tenant.id}"
    tenant_required = [
        "whatsapp_token",
        "whatsapp_phone_number_id",
        "whatsapp_verify_token",
        "whatsapp_app_secret",
    ]
    configured_settings, missing_settings = _tenant_setting_state(tenant_settings, tenant_required)
    warnings = _public_url_warnings(public_url_status)
    if public_url_status == ChannelWebhookPublicUrlStatus.https_ready:
        configured_settings.append("API_PUBLIC_URL")
    else:
        missing_settings.append("API_PUBLIC_URL_HTTPS")

    ready = not missing_settings
    return ChannelWebhookDiagnosticItem(
        key="whatsapp",
        label="WhatsApp Cloud API",
        provider="meta",
        status=(
            ChannelWebhookDiagnosticStatus.ready
            if ready
            else ChannelWebhookDiagnosticStatus.needs_setup
        ),
        summary=(
            "WhatsApp webhook verification and signed message callbacks are ready."
            if ready
            else "WhatsApp needs Cloud API credentials, app secret and a public HTTPS callback URL."
        ),
        inbound_webhook_url=webhook_url,
        required_settings=[*tenant_required, "API_PUBLIC_URL"],
        configured_settings=configured_settings,
        missing_settings=missing_settings,
        setup_steps=[
            "Open Meta App Dashboard > WhatsApp > Configuration.",
            "Paste the webhook URL as Callback URL.",
            "Paste whatsapp_verify_token as Verify Token.",
            "Subscribe to messages and message status fields.",
            "Set whatsapp_app_secret so inbound callbacks require x-hub-signature-256.",
        ],
        security_notes=[
            "GET verification uses whatsapp_verify_token.",
            "POST callbacks require x-hub-signature-256 when whatsapp_app_secret is configured.",
            "Diagnostics never return access token, verify token or app secret values.",
        ],
        warnings=warnings,
        setup_url="/settings/channels#whatsapp",
        docs_url="/docs#whatsapp",
        test_mode=not ready,
    )


def _tenant_setting_state(
    tenant_settings: Mapping[str, object],
    setting_names: Sequence[str],
) -> tuple[list[str], list[str]]:
    configured = [name for name in setting_names if _has_value(tenant_settings.get(name))]
    missing = [name for name in setting_names if name not in configured]
    return configured, missing


def _normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    return normalized or "http://localhost:8000"


def _public_url_status(public_base_url: str) -> ChannelWebhookPublicUrlStatus:
    if not public_base_url:
        return ChannelWebhookPublicUrlStatus.missing
    if public_base_url.startswith("https://"):
        return ChannelWebhookPublicUrlStatus.https_ready
    return ChannelWebhookPublicUrlStatus.local_only


def _public_url_warnings(status: ChannelWebhookPublicUrlStatus) -> list[str]:
    if status == ChannelWebhookPublicUrlStatus.https_ready:
        return []
    if status == ChannelWebhookPublicUrlStatus.missing:
        return ["Set API_PUBLIC_URL to the public HTTPS API origin before live webhook setup."]
    return ["Current API_PUBLIC_URL is local or non-HTTPS; live providers require public HTTPS."]


def _has_value(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
