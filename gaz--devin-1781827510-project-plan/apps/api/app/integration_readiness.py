from collections.abc import Mapping
from datetime import UTC, datetime

from app.schemas import (
    IntegrationReadinessItem,
    IntegrationReadinessOverallStatus,
    IntegrationReadinessResponse,
    IntegrationReadinessStatus,
)
from app.settings import Settings


def build_integration_readiness(
    tenant_settings: Mapping[str, object] | None,
    settings: Settings,
) -> IntegrationReadinessResponse:
    tenant_values = tenant_settings or {}
    items = [
        _llm_item(tenant_values, settings),
        _speech_item(tenant_values, settings),
        _web_widget_item(),
        _tenant_or_env_item(
            key="telegram",
            label="Telegram",
            category="Messaging",
            tenant_values=tenant_values,
            tenant_keys=["telegram_bot_token"],
            env_keys=["TELEGRAM_BOT_TOKEN"],
            env_configured=bool(settings.telegram_bot_token),
            setup_url="/settings/channels#telegram",
            docs_url="/docs#telegram",
            stub_summary="Telegram Bot API is in local stub mode until a bot token is configured.",
            configured_summary="Telegram Bot API credentials are configured.",
        ),
        _tenant_item(
            key="vk",
            label="VK Communities",
            category="Messaging",
            tenant_values=tenant_values,
            tenant_keys=["vk_group_token", "vk_confirmation_code"],
            setup_url="/settings/channels#vk",
            docs_url="/docs#vk",
            stub_summary="VK webhook handling is in setup mode until token and confirmation code are configured.",
            configured_summary="VK community token and confirmation code are configured.",
        ),
        _tenant_item(
            key="whatsapp",
            label="WhatsApp Cloud API",
            category="Messaging",
            tenant_values=tenant_values,
            tenant_keys=[
                "whatsapp_token",
                "whatsapp_phone_number_id",
                "whatsapp_verify_token",
                "whatsapp_app_secret",
            ],
            setup_url="/settings/channels#whatsapp",
            docs_url="/docs#whatsapp",
            stub_summary="WhatsApp is in setup mode until Meta Cloud API credentials are configured.",
            configured_summary="WhatsApp Cloud API credentials are configured.",
        ),
        _tenant_or_env_item(
            key="twilio_voice",
            label="Twilio Voice/SMS",
            category="Voice",
            tenant_values=tenant_values,
            tenant_keys=["twilio_account_sid", "twilio_auth_token", "twilio_phone_number"],
            env_keys=["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"],
            env_configured=bool(
                settings.twilio_account_sid
                and settings.twilio_auth_token
                and settings.twilio_phone_number
            ),
            setup_url="/settings/channels#twilio",
            docs_url="/docs#twilio",
            stub_summary="Outbound calls use the simulator until Twilio credentials are configured.",
            configured_summary="Twilio voice/SMS credentials are configured.",
        ),
        _tenant_or_env_item(
            key="sip_asterisk",
            label="SIP/Asterisk",
            category="Voice",
            tenant_values=tenant_values,
            tenant_keys=["sip_server", "sip_provider", "sip_login", "sip_password"],
            env_keys=["ASTERISK_ARI_USERNAME", "ASTERISK_ARI_PASSWORD"],
            env_configured=bool(settings.asterisk_ari_username and settings.asterisk_ari_password),
            setup_url="/settings/channels#sip",
            docs_url="/docs#sip",
            stub_summary="SIP/Asterisk is in local architecture mode until SIP or ARI credentials are configured.",
            configured_summary="SIP/Asterisk credentials are configured.",
        ),
        _tenant_or_env_item(
            key="yookassa",
            label="YooKassa",
            category="Payments",
            tenant_values=tenant_values,
            tenant_keys=["yookassa_shop_id", "yookassa_secret_key"],
            env_keys=["YOOKASSA_SHOP_ID", "YOOKASSA_SECRET_KEY"],
            env_configured=bool(settings.yookassa_shop_id and settings.yookassa_secret_key),
            setup_url="/settings/channels#yookassa",
            docs_url="/docs#yookassa",
            stub_summary="Payments use local checkout simulation until YooKassa credentials are configured.",
            configured_summary="YooKassa credentials are configured.",
        ),
        _tenant_or_env_item(
            key="iiko",
            label="iikoCloud",
            category="CRM/Orders",
            tenant_values=tenant_values,
            tenant_keys=["iiko_api_login", "iiko_organization_id", "iiko_terminal_group_id"],
            env_keys=["IIKO_API_LOGIN", "IIKO_API_PASSWORD"],
            env_configured=bool(settings.iiko_api_login and settings.iiko_api_password),
            setup_url="/settings/channels#iiko",
            docs_url="/docs#iiko",
            stub_summary="iiko order/menu sync is in setup mode until iiko credentials are configured.",
            configured_summary="iikoCloud credentials are configured.",
        ),
    ]
    blocking_missing = any(
        item.blocking and item.status != IntegrationReadinessStatus.configured
        for item in items
    )
    if blocking_missing:
        overall_status = IntegrationReadinessOverallStatus.action_required
    elif any(item.status != IntegrationReadinessStatus.configured for item in items):
        overall_status = IntegrationReadinessOverallStatus.mock_mode
    else:
        overall_status = IntegrationReadinessOverallStatus.ready
    return IntegrationReadinessResponse(
        status=overall_status,
        checked_at=datetime.now(UTC),
        items=items,
    )


def _llm_item(
    tenant_values: Mapping[str, object],
    settings: Settings,
) -> IntegrationReadinessItem:
    tenant_configured = _has_value(tenant_values.get("openai_api_key"))
    env_openai_configured = bool(settings.openai_api_key)
    env_vllm_configured = bool(settings.vllm_base_url)
    configured = tenant_configured or env_openai_configured or env_vllm_configured
    required_settings = ["openai_api_key", "OPENAI_API_KEY", "VLLM_BASE_URL"]
    configured_settings: list[str] = []
    if tenant_configured:
        configured_settings.append("openai_api_key")
    if env_openai_configured:
        configured_settings.append("OPENAI_API_KEY")
    if env_vllm_configured:
        configured_settings.append("VLLM_BASE_URL")

    return IntegrationReadinessItem(
        key="llm",
        label="LLM provider",
        category="AI",
        status=(
            IntegrationReadinessStatus.configured
            if configured
            else IntegrationReadinessStatus.local_stub
        ),
        summary=(
            "Real LLM provider is configured."
            if configured
            else "Mock LLM is active until OpenAI or local vLLM credentials are configured."
        ),
        required_settings=required_settings,
        configured_settings=configured_settings,
        missing_settings=[] if configured else required_settings,
        setup_url="/settings/channels#openai",
        docs_url="/docs#llm",
        blocking=not configured,
    )


def _speech_item(
    tenant_values: Mapping[str, object],
    settings: Settings,
) -> IntegrationReadinessItem:
    configured = _has_value(tenant_values.get("openai_api_key")) or bool(settings.openai_api_key)
    required_settings = ["openai_api_key", "OPENAI_API_KEY"]
    configured_settings: list[str] = []
    if _has_value(tenant_values.get("openai_api_key")):
        configured_settings.append("openai_api_key")
    if settings.openai_api_key:
        configured_settings.append("OPENAI_API_KEY")
    return IntegrationReadinessItem(
        key="speech_stt_tts",
        label="Speech STT/TTS",
        category="Voice",
        status=(
            IntegrationReadinessStatus.configured
            if configured
            else IntegrationReadinessStatus.local_stub
        ),
        summary=(
            "Speech provider credentials are configured."
            if configured
            else "Voice preview uses local/no-audio mode until speech credentials are configured."
        ),
        required_settings=required_settings,
        configured_settings=configured_settings,
        missing_settings=[] if configured else required_settings,
        setup_url="/settings/channels#openai",
        docs_url="/docs#speech",
        blocking=False,
    )


def _web_widget_item() -> IntegrationReadinessItem:
    return IntegrationReadinessItem(
        key="web_widget",
        label="Web widget",
        category="Messaging",
        status=IntegrationReadinessStatus.configured,
        summary="Web widget is available without external provider credentials.",
        required_settings=[],
        configured_settings=["NEXT_PUBLIC_API_URL"],
        missing_settings=[],
        setup_url="/dashboard",
        docs_url="/docs#web-widget",
        blocking=False,
    )


def _tenant_item(
    *,
    key: str,
    label: str,
    category: str,
    tenant_values: Mapping[str, object],
    tenant_keys: list[str],
    setup_url: str,
    docs_url: str,
    stub_summary: str,
    configured_summary: str,
) -> IntegrationReadinessItem:
    configured_settings = [item for item in tenant_keys if _has_value(tenant_values.get(item))]
    missing_settings = [item for item in tenant_keys if item not in configured_settings]
    configured = not missing_settings
    return IntegrationReadinessItem(
        key=key,
        label=label,
        category=category,
        status=(
            IntegrationReadinessStatus.configured
            if configured
            else IntegrationReadinessStatus.needs_setup
        ),
        summary=configured_summary if configured else stub_summary,
        required_settings=tenant_keys,
        configured_settings=configured_settings,
        missing_settings=missing_settings,
        setup_url=setup_url,
        docs_url=docs_url,
        blocking=False,
    )


def _tenant_or_env_item(
    *,
    key: str,
    label: str,
    category: str,
    tenant_values: Mapping[str, object],
    tenant_keys: list[str],
    env_keys: list[str],
    env_configured: bool,
    setup_url: str,
    docs_url: str,
    stub_summary: str,
    configured_summary: str,
) -> IntegrationReadinessItem:
    configured_settings = [item for item in tenant_keys if _has_value(tenant_values.get(item))]
    missing_tenant_settings = [item for item in tenant_keys if item not in configured_settings]
    tenant_configured = not missing_tenant_settings
    if env_configured:
        configured_settings.extend(env_keys)
    configured = tenant_configured or env_configured
    missing_settings = [] if configured else [*tenant_keys, *env_keys]
    status = (
        IntegrationReadinessStatus.configured
        if configured
        else IntegrationReadinessStatus.local_stub
    )
    return IntegrationReadinessItem(
        key=key,
        label=label,
        category=category,
        status=status,
        summary=configured_summary if configured else stub_summary,
        required_settings=[*tenant_keys, *env_keys],
        configured_settings=configured_settings,
        missing_settings=missing_settings,
        setup_url=setup_url,
        docs_url=docs_url,
        blocking=False,
    )


def _has_value(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
