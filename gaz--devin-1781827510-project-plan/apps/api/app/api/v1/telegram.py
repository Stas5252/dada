from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, Request

from app.channels import ChannelType, OutboundMessage
from app.channels.telegram_adapter import TelegramChannelAdapter, parse_telegram_update
from app.orchestrator import AgentOrchestrator
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
    telegram: TelegramChannelAdapter = Depends(get_telegram_adapter),
) -> dict[str, str]:
    """
    Handle incoming Telegram messages.
    URL format: /api/v1/webhooks/telegram/{agent_id}
    """
    try:
        update = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    # Deduplication: skip already-processed updates
    update_id = str(update.get("update_id", ""))
    if update_id and telegram.is_duplicate_update(update_id):
        return {"status": "ok", "detail": "duplicate"}

    # Parse into normalized MessageEvent
    event = parse_telegram_update(update)
    if not event:
        # Ignore unsupported updates gracefully (edits, reactions, etc.)
        return {"status": "ok"}

    # Find the agent's tenant
    tenant_id_str = await _find_tenant_for_agent(agent_id, app_store)
    if not tenant_id_str:
        return {"status": "error", "message": "Agent not found"}

    tenant_uuid = UUID(tenant_id_str)

    from app.api.v1.dependencies import check_billing_limit
    try:
        check_billing_limit(tenant_uuid, app_store)
    except HTTPException as e:
        if e.status_code == 402:
            limit_message = (
                "Уведомление: Лимит сообщений для этого ИИ-агента исчерпан. "
                "Пожалуйста, обновите тарифный план в личном кабинете CallForce."
            )
            outbound = OutboundMessage(
                channel=ChannelType.telegram,
                external_chat_id=event.external_chat_id,
                text=limit_message,
                reply_to_message_id=event.external_message_id,
            )
            await telegram.send_message(outbound)
            return {"status": "error", "message": "Billing limit reached"}
        raise e

    agent_uuid = UUID(agent_id)

    # Map Telegram chat_id -> stable conversation UUID
    conversation_uuid = uuid5(NAMESPACE_URL, f"tg_chat:{event.external_chat_id}:{agent_id}")

    # Process message via Orchestrator
    orchestrator = AgentOrchestrator(store=app_store, settings=settings)

    response_text = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        customer_message=event.text,
        channel="telegram",
    )

    recorded = app_store.record_chat_turn(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        channel="telegram",
        customer_text=event.text,
        agent_response_text=response_text,
    )
    if not recorded:
        return {"status": "error", "message": "Agent not found"}

    # Send response back via Telegram
    outbound = OutboundMessage(
        channel=ChannelType.telegram,
        external_chat_id=event.external_chat_id,
        text=response_text,
        reply_to_message_id=event.external_message_id,
    )
    result = await telegram.send_message(outbound)

    if not result.success:
        return {"status": "error", "message": result.error}

    return {"status": "ok"}


async def _find_tenant_for_agent(agent_id: str, app_store: AppStore) -> str | None:
    """
    Find the tenant that owns a given agent.
    Iterates through all tenants to find the agent. In production with SQL,
    this would be a simple SELECT tenant_id FROM agents WHERE id = ?.
    """
    try:
        agent_uuid = UUID(agent_id)
    except ValueError:
        return None

    # Try to find agent globally by checking known tenants
    # For InMemoryStore, we can access agents directly
    if hasattr(app_store, "agents"):
        agent = app_store.agents.get(agent_uuid)
        if agent:
            return str(agent.tenant_id)

    # Fallback: try demo tenant
    from app.settings import get_settings

    settings = get_settings()
    agent = app_store.get_agent(UUID(settings.demo_tenant_id), agent_uuid)
    if agent:
        return settings.demo_tenant_id

    return None
