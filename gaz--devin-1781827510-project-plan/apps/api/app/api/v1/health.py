from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.settings import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str
    version: str
    checked_at: datetime


class ProviderReadiness(BaseModel):
    provider: str
    status: Literal["configured", "missing_secret", "local_stub"]
    detail: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded", "mock_only"]
    service: str
    environment: str
    store_backend: str
    rls_enabled: bool
    providers: list[ProviderReadiness]
    checked_at: datetime


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.app_env,
        version=settings.api_version,
        checked_at=datetime.now(UTC),
    )


@router.get("/readiness", response_model=ReadinessResponse)
async def readiness(settings: Settings = Depends(get_settings)) -> ReadinessResponse:
    providers = [
        _llm_readiness(settings),
        _provider_readiness(
            provider="telegram",
            configured=bool(settings.telegram_bot_token),
            detail="TELEGRAM_BOT_TOKEN",
        ),
        _provider_readiness(
            provider="yookassa",
            configured=bool(settings.yookassa_shop_id and settings.yookassa_secret_key),
            detail="YOOKASSA_SHOP_ID + YOOKASSA_SECRET_KEY",
        ),
        _provider_readiness(
            provider="iiko",
            configured=bool(settings.iiko_api_login and settings.iiko_api_password),
            detail="IIKO_API_LOGIN + IIKO_API_PASSWORD",
        ),
        _provider_readiness(
            provider="twilio_voice",
            configured=bool(
                settings.twilio_account_sid
                and settings.twilio_auth_token
                and settings.twilio_phone_number
            ),
            detail="TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_PHONE_NUMBER",
        ),
        _provider_readiness(
            provider="speech_stt_tts",
            configured=bool(settings.openai_api_key or settings.yandex_api_key or settings.deepgram_api_key),
            detail="YANDEX_API_KEY, DEEPGRAM_API_KEY or OPENAI_API_KEY",
        ),
        _provider_readiness(
            provider="asterisk_ari",
            configured=bool(settings.asterisk_ari_username and settings.asterisk_ari_password),
            detail="ASTERISK_ARI_USERNAME + ASTERISK_ARI_PASSWORD",
        ),
    ]
    
    if any(p.status == "missing_secret" for p in providers):
        status = "degraded"
    elif any(p.status == "local_stub" for p in providers):
        status = "mock_only"
    else:
        status = "ready"

    return ReadinessResponse(
        status=status,
        service=settings.service_name,
        environment=settings.app_env,
        store_backend=settings.store_backend,
        rls_enabled=settings.store_backend == "sqlalchemy",
        providers=providers,
        checked_at=datetime.now(UTC),
    )


def _llm_readiness(settings: Settings) -> ProviderReadiness:
    provider = settings.llm_provider.lower()
    if settings.vllm_base_url:
        return ProviderReadiness(
            provider="llm",
            status="configured",
            detail=(
                "Local OpenAI-compatible LLM endpoint is configured " f"({settings.vllm_model})."
            ),
        )
    if settings.openai_api_key:
        return ProviderReadiness(
            provider="llm",
            status="configured",
            detail=(
                "OpenAI LLM credentials are configured "
                f"({settings.openai_fast_model}/{settings.openai_smart_model})."
            ),
        )
    if provider in {"local", "local_vllm", "vllm"}:
        return ProviderReadiness(
            provider="llm",
            status="missing_secret",
            detail="LLM_PROVIDER requests local AI, but VLLM_BASE_URL is not configured.",
        )
    if provider == "openai":
        return ProviderReadiness(
            provider="llm",
            status="missing_secret",
            detail="LLM_PROVIDER requests OpenAI, but OPENAI_API_KEY is not configured.",
        )
    return ProviderReadiness(
        provider="llm",
        status="local_stub",
        detail="Mock LLM is active until VLLM_BASE_URL or OPENAI_API_KEY is configured.",
    )


def _provider_readiness(
    *,
    provider: str,
    configured: bool,
    detail: str,
) -> ProviderReadiness:
    if configured:
        return ProviderReadiness(
            provider=provider,
            status="configured",
            detail="Real provider credentials are configured.",
        )
    return ProviderReadiness(
        provider=provider,
        status="local_stub",
        detail=f"Local stub is active until {detail} is configured.",
    )
