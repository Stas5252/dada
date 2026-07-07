from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.dependencies import find_tenant_for_agent
from app.channel_policy import (
    append_channel_opt_out_notice,
    audit_channel_policy_auto_reply_block,
    channel_policy_for_settings,
    evaluate_channel_auto_reply_policy,
)
from app.channels import ChannelType, OutboundMessage
from app.channels.telegram_adapter import parse_telegram_update
from app.encryption import decrypt_token
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
) -> dict[str, str]:
    """
    Handle incoming Telegram messages.
    URL format: /api/v1/webhooks/telegram/{agent_id}
    """
    try:
        update = await request.json()
        if not isinstance(update, dict):
            raise ValueError("Expected JSON dictionary")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    # Find the agent's tenant
    tenant_id_str = find_tenant_for_agent(agent_id, app_store)
    if not tenant_id_str:
        return {"status": "error", "message": "Agent not found"}

    tenant_uuid = UUID(tenant_id_str)
    agent_uuid = UUID(agent_id)
    tenant = app_store.get_tenant(tenant_uuid)
    tenant_settings = tenant.settings if tenant else None
    channel_policy = channel_policy_for_settings(tenant_settings, "telegram")
    
    agent = app_store.get_agent(tenant_uuid, agent_uuid)
    if not agent or not agent.telegram_bot_token:
        return {"status": "error", "message": "Agent not configured for Telegram"}
        
    decrypted_token = decrypt_token(agent.telegram_bot_token, settings.access_token_secret)
    if not decrypted_token:
        return {"status": "error", "message": "Failed to decrypt Telegram bot token"}
        
    secret_token_header = request.headers.get("x-telegram-bot-api-secret-token")
    import hashlib
    expected_secret = hashlib.sha256(decrypted_token.encode("utf-8")).hexdigest()
    if secret_token_header != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid secret token")
        
    telegram = get_telegram_adapter(bot_token=decrypted_token)

    # Deduplication: skip already-processed updates
    update_id = str(update.get("update_id", ""))
    if update_id and telegram.is_duplicate_update(update_id):
        return {"status": "ok", "detail": "duplicate"}

    # Parse into normalized MessageEvent
    event = parse_telegram_update(update)
    if not event:
        # Ignore unsupported updates gracefully (edits, reactions, etc.)
        return {"status": "ok"}

    # Map Telegram chat_id -> stable conversation UUID
    conversation_uuid = uuid5(NAMESPACE_URL, f"tg_chat:{event.external_chat_id}:{agent_id}")

    # Resolve or create customer
    customer = app_store.get_customer_by_external_id(
        tenant_id=tenant_uuid,
        channel="telegram",
        external_id=event.external_chat_id,
    )
    if not customer:
        customer = app_store.create_customer(
            tenant_id=tenant_uuid,
            channel="telegram",
            external_id=event.external_chat_id,
            name=event.sender_name,
        )
    elif event.sender_name and customer.name != event.sender_name:
        customer = (
            app_store.update_customer(
                tenant_id=tenant_uuid,
                customer_id=customer.id,
                name=event.sender_name,
            )
            or customer
        )

    existing_suppression = app_store.find_contact_suppression(
        tenant_uuid,
        "telegram",
        external_id=event.external_chat_id,
        phone=customer.phone,
    )
    if existing_suppression:
        app_store.create_audit_log(
            event_type="contact_suppression.inbound_ignored",
            tenant_id=tenant_uuid,
            details={
                "channel": "telegram",
                "contact_type": existing_suppression.contact_type,
                "source": "telegram_webhook",
                "suppression_id": str(existing_suppression.id),
                "value": existing_suppression.value,
            },
        )
        return {"status": "ok", "message": "suppressed"}

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

    # Process message via Orchestrator
    orchestrator = AgentOrchestrator(store=app_store, settings=settings)

    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        customer_message=event.text,
        channel="telegram",
    )
    response_text = orchestrator_result.response_text
    forced_status = orchestrator_result.forced_status
    forced_resolution_status = orchestrator_result.forced_resolution_status
    auto_reply_decision = evaluate_channel_auto_reply_policy(
        app_store,
        tenant_id=tenant_uuid,
        conversation_id=conversation_uuid,
        policy=channel_policy,
    )
    if auto_reply_decision.allowed:
        response_text = append_channel_opt_out_notice(
            response_text,
            policy=channel_policy,
            channel="telegram",
        )
    else:
        forced_status = auto_reply_decision.forced_status
        forced_resolution_status = auto_reply_decision.forced_resolution_status

    recorded = app_store.record_chat_turn(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        channel="telegram",
        customer_text=event.text,
        agent_response_text=response_text,
        customer_id=customer.id,
        confidence_score=orchestrator_result.confidence_score,
        forced_status=forced_status,
        forced_resolution_status=forced_resolution_status,
    )
    if not recorded:
        return {"status": "error", "message": "Agent not found"}

    if orchestrator_result.guardrail_code == "opt_out_requested":
        app_store.record_contact_suppression(
            tenant_uuid,
            "telegram",
            "external_id",
            event.external_chat_id,
            reason="opt_out_requested",
            source="telegram_guardrail",
        )

    if not auto_reply_decision.allowed:
        audit_channel_policy_auto_reply_block(
            app_store,
            tenant_id=tenant_uuid,
            channel="telegram",
            conversation_id=conversation_uuid,
            source="telegram_webhook",
            policy=channel_policy,
            resolution_status=auto_reply_decision.forced_resolution_status,
            block_reason=auto_reply_decision.block_reason or "automation_mode",
            agent_reply_count=auto_reply_decision.agent_reply_count,
        )
        return {"status": "ok", "message": "channel_policy_auto_reply_blocked"}

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
