from fastapi import APIRouter, Depends, Request

from app.api.v1.webhooks import generic_webhook_handler
from app.channels import ChannelType
from app.service_factory import get_telegram_adapter
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/webhooks/telegram", tags=["telegram"])


@router.post("/{agent_id}")
async def telegram_webhook(
    agent_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, str]:
    """
    Handle incoming Telegram messages.
    URL format: /api/v1/webhooks/telegram/{agent_id}
    """
    # Note: Telegram adapter normally requires bot_token to send messages.
    # But since generic_webhook_handler verifies first, it will instantiate a 
    # dummy adapter, then if it needs to send it creates the real one?
    # Actually, get_telegram_adapter takes an optional bot_token and handles it.
    # The Generic Webhook Handler will call adapter.send_message, but wait!
    # Telegram adapter requires `bot_token` to be initialized to send messages!
    
    # We should let the generic handler pass the adapter, or we initialize it here?
    # We can fetch the agent here to get the bot token.
    # Or, the GenericHandler can resolve the adapter dynamically!
    
    # Wait, the current `get_telegram_adapter` is a factory.
    # If we initialize it without a bot token, it acts as a stub.
    # We can fetch the agent here to initialize the adapter properly:
    from uuid import UUID
    from app.encryption import decrypt_token
    from app.api.v1.dependencies import find_tenant_for_agent
    
    tenant_id_str = find_tenant_for_agent(agent_id, app_store)
    if not tenant_id_str:
        return {"status": "error", "message": "Agent not found"}
        
    tenant_uuid = UUID(tenant_id_str)
    agent = app_store.get_agent(tenant_uuid, UUID(agent_id))
    bot_token = ""
    if agent and agent.telegram_bot_token:
        decrypted = decrypt_token(agent.telegram_bot_token, settings.access_token_secret)
        if decrypted:
            bot_token = decrypted
            
    telegram_adapter = get_telegram_adapter(bot_token=bot_token)

    response = await generic_webhook_handler(
        channel_type=ChannelType.telegram,
        request=request,
        adapter=telegram_adapter,
        settings=settings,
        app_store=app_store,
        agent_id=agent_id,
    )
    # The handler returns Response | dict
    return response
