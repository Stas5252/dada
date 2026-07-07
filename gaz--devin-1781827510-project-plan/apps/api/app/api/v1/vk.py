from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.channel_policy import (
    append_channel_opt_out_notice,
    audit_channel_policy_auto_reply_block,
    channel_policy_for_settings,
    evaluate_channel_auto_reply_policy,
)
from app.channels import ChannelType, OutboundMessage
from app.channels.vk_adapter import parse_vk_update
from app.orchestrator import AgentOrchestrator
from app.service_factory import get_vk_adapter
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/webhooks/vk", tags=["vk"])


@router.post("/{tenant_id}", response_class=PlainTextResponse)
async def vk_webhook(
    tenant_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> PlainTextResponse:
    """
    Handle incoming VK Community messages.
    URL format: /api/v1/webhooks/vk/{tenant_id}
    """
    try:
        update = await request.json()
        if not isinstance(update, dict):
            raise ValueError("Expected JSON dictionary")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        return PlainTextResponse("ok")

    vk_secret_key = tenant.settings.get("vk_secret_key")
    if vk_secret_key and update.get("secret") != vk_secret_key:
        raise HTTPException(status_code=403, detail="Invalid VK secret key")

    # VK Confirmation Challenge
    if update.get("type") == "confirmation":
        vk_confirmation_code = tenant.settings.get("vk_confirmation_code", "")
        if isinstance(vk_confirmation_code, str) and vk_confirmation_code:
            return PlainTextResponse(vk_confirmation_code)
        return PlainTextResponse("ok")

    # Find the default agent for this tenant (VK usually routes to the primary agent)
    # We will just pick the first active agent, or ideally we'd configure a default_agent_id in settings
    agents = app_store.list_agents(tenant_uuid)
    agent = next((a for a in agents if a.status == "published"), None)
    
    if not agent:
        return PlainTextResponse("ok")
    channel_policy = channel_policy_for_settings(tenant.settings, "vk")

    vk_token = tenant.settings.get("vk_group_token")
    if not isinstance(vk_token, str) or not vk_token:
        return PlainTextResponse("ok")

    vk = get_vk_adapter(group_token=vk_token)

    # Parse into normalized MessageEvent
    event = parse_vk_update(update)
    if not event:
        # Ignore unsupported updates
        return PlainTextResponse("ok")

    if vk.is_duplicate_update(event.external_message_id):
        return PlainTextResponse("ok")

    # Map VK peer_id -> stable conversation UUID
    conversation_uuid = uuid5(NAMESPACE_URL, f"vk_chat:{event.external_chat_id}:{agent.id}")

    # Resolve or create customer
    customer = app_store.get_customer_by_external_id(
        tenant_id=tenant_uuid,
        channel="vk",
        external_id=event.external_chat_id,
    )
    if not customer:
        customer = app_store.create_customer(
            tenant_id=tenant_uuid,
            channel="vk",
            external_id=event.external_chat_id,
            name=event.sender_name,
        )
    elif event.sender_name and customer.name != event.sender_name:
        customer = app_store.update_customer(
            tenant_id=tenant_uuid,
            customer_id=customer.id,
            name=event.sender_name,
        ) or customer

    existing_suppression = app_store.find_contact_suppression(
        tenant_uuid,
        "vk",
        external_id=event.external_chat_id,
        phone=customer.phone,
    )
    if existing_suppression:
        app_store.create_audit_log(
            event_type="contact_suppression.inbound_ignored",
            tenant_id=tenant_uuid,
            details={
                "channel": "vk",
                "contact_type": existing_suppression.contact_type,
                "source": "vk_webhook",
                "suppression_id": str(existing_suppression.id),
                "value": existing_suppression.value,
            },
        )
        return PlainTextResponse("ok")

    from app.api.v1.dependencies import check_billing_limit

    try:
        check_billing_limit(tenant_uuid, app_store)
    except HTTPException as e:
        if e.status_code == 402:
            limit_message = (
                "Уведомление: Лимит сообщений исчерпан. Пожалуйста, обновите тарифный план."
            )
            outbound = OutboundMessage(
                channel=ChannelType.vk,
                external_chat_id=event.external_chat_id,
                text=limit_message,
                reply_to_message_id=event.external_message_id,
            )
            await vk.send_message(outbound)
            return PlainTextResponse("ok")
        raise e

    # Run Orchestrator
    orchestrator = AgentOrchestrator(store=app_store, settings=settings)
    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent.id,
        conversation_id=conversation_uuid,
        customer_message=event.text,
        channel="vk",
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
            channel="vk",
        )
    else:
        forced_status = auto_reply_decision.forced_status
        forced_resolution_status = auto_reply_decision.forced_resolution_status

    # Record turn
    app_store.record_chat_turn(
        tenant_id=tenant_uuid,
        agent_id=agent.id,
        conversation_id=conversation_uuid,
        channel="vk",
        customer_text=event.text,
        agent_response_text=response_text,
        customer_id=customer.id,
        confidence_score=orchestrator_result.confidence_score,
        forced_status=forced_status,
        forced_resolution_status=forced_resolution_status,
    )

    if orchestrator_result.guardrail_code == "opt_out_requested":
        app_store.record_contact_suppression(
            tenant_uuid,
            "vk",
            "external_id",
            event.external_chat_id,
            reason="opt_out_requested",
            source="vk_guardrail",
        )

    if not auto_reply_decision.allowed:
        audit_channel_policy_auto_reply_block(
            app_store,
            tenant_id=tenant_uuid,
            channel="vk",
            conversation_id=conversation_uuid,
            source="vk_webhook",
            policy=channel_policy,
            resolution_status=auto_reply_decision.forced_resolution_status,
            block_reason=auto_reply_decision.block_reason or "automation_mode",
            agent_reply_count=auto_reply_decision.agent_reply_count,
        )
        return PlainTextResponse("ok")

    # Send response back to VK
    outbound = OutboundMessage(
        channel=ChannelType.vk,
        external_chat_id=event.external_chat_id,
        text=response_text,
        reply_to_message_id=event.external_message_id,
    )
    await vk.send_message(outbound)

    return PlainTextResponse("ok")
