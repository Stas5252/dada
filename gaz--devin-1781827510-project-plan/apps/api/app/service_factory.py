from functools import lru_cache

from app.billing_service import BillingService
from app.channels.telegram_adapter import TelegramChannelAdapter
from app.channels.vk_adapter import VKChannelAdapter
from app.channels.whatsapp_adapter import WhatsAppChannelAdapter
from app.contracts.integrations import WebhookSigningConfig
from app.integration_services import (
    LocalIikoAdapter,
    LocalWebhookSigner,
    LocalYooKassaAdapter,
)
from app.voice_service import VoiceSessionService


@lru_cache
def get_iiko_adapter() -> LocalIikoAdapter:
    return LocalIikoAdapter()


@lru_cache(maxsize=100)
def get_telegram_adapter(bot_token: str | None = None) -> TelegramChannelAdapter:
    from app.settings import get_settings

    token = bot_token or get_settings().telegram_bot_token
    return TelegramChannelAdapter(bot_token=token)


@lru_cache
def get_yookassa_adapter() -> LocalYooKassaAdapter:
    return LocalYooKassaAdapter()


@lru_cache(maxsize=100)
def get_vk_adapter(group_token: str) -> VKChannelAdapter:
    return VKChannelAdapter(group_token=group_token)


@lru_cache(maxsize=100)
def get_whatsapp_adapter(access_token: str, phone_number_id: str) -> WhatsAppChannelAdapter:
    return WhatsAppChannelAdapter(access_token=access_token, phone_number_id=phone_number_id)



@lru_cache
def get_voice_service() -> VoiceSessionService:
    return VoiceSessionService()


@lru_cache
def get_billing_service() -> BillingService:
    from app.settings import get_settings

    settings = get_settings()
    if settings.store_backend == "sqlalchemy":
        from app.billing_service import SqlAlchemyBillingLedger
        from app.database import build_engine, build_session_factory

        engine = build_engine(settings.database_url)
        session_factory = build_session_factory(engine)
        return BillingService(ledger=SqlAlchemyBillingLedger(session_factory))
    return BillingService()


def get_webhook_signer(tenant_id: str) -> LocalWebhookSigner:
    return LocalWebhookSigner(
        config=WebhookSigningConfig(tenant_id=tenant_id, key_id="local-default"),
        signing_key=b"local-webhook-signing-key",
    )


@lru_cache
def get_agent_orchestrator() -> "AgentOrchestrator":
    from app.settings import get_settings
    from app.store_factory import get_app_store
    from app.orchestrator import AgentOrchestrator
    
    return AgentOrchestrator(store=get_app_store(), settings=get_settings())

