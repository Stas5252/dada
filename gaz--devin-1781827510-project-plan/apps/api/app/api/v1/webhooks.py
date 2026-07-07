from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.api.v1.dependencies import check_billing_limit, find_tenant_for_agent
from app.channel_policy import (
    append_channel_opt_out_notice,
    audit_channel_policy_auto_reply_block,
    channel_policy_for_settings,
    evaluate_channel_auto_reply_policy,
)
from app.channels import ChannelAdapter, ChannelType, OutboundMessage
from app.orchestrator import AgentOrchestrator
from app.settings import Settings
from app.store_factory import AppStore


async def generic_webhook_handler(
    channel_type: ChannelType,
    request: Request,
    adapter: ChannelAdapter,
    settings: Settings,
    app_store: AppStore,
    agent_id: str | None = None,
    tenant_id: str | None = None,
) -> Response | dict[str, str]:
    """
    Generic webhook pipeline for processing incoming messages from various channels.
    """
    try:
        if request.method == "POST":
            # Just grab the json if we can, else ignore (adapter verify_request might do something else)
            try:
                update = await request.json()
            except Exception:
                update = {}
        else:
            update = {}
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid request") from exc

    if agent_id:
        # Find the agent's tenant
        tenant_id_str = find_tenant_for_agent(agent_id, app_store)
        if not tenant_id_str:
            return JSONResponse({"status": "error", "message": "Agent not found"}, status_code=404)
        tenant_uuid = UUID(tenant_id_str)
        agent_uuid = UUID(agent_id)
        agent = app_store.get_agent(tenant_uuid, agent_uuid)
    elif tenant_id:
        tenant_uuid = UUID(tenant_id)
        agents = app_store.list_agents(tenant_uuid)
        agent = next((a for a in agents if a.status == "published"), None)
        # We do not return 404 here because VK/WhatsApp verification requests might arrive before an agent is published.
        agent_uuid = agent.id if agent else None
    else:
        return JSONResponse({"status": "error", "message": "Must provide agent_id or tenant_id"}, status_code=400)

    tenant = app_store.get_tenant(tenant_uuid)
    tenant_settings = tenant.settings if tenant else None

    # Let the adapter verify the request (signatures, challenges, tokens)
    verification_response = await adapter.verify_request(request, agent, settings)
    if verification_response is not None:
        return verification_response

    if not adapter.is_configured:
        return JSONResponse({"status": "error", "message": f"Agent not configured for {channel_type.value}"}, status_code=400)

    # Deduplication
    if update and adapter.is_duplicate_update(update):
        return {"status": "ok", "detail": "duplicate"}

    # Parse into normalized MessageEvent
    event = adapter.parse_update(update)
    if not event:
        # Ignore unsupported updates gracefully
        return {"status": "ok"}

    channel_policy = channel_policy_for_settings(tenant_settings, channel_type.value)

    # Map external_chat_id -> stable conversation UUID
    conversation_uuid = uuid5(NAMESPACE_URL, f"{channel_type.value}_chat:{event.external_chat_id}:{agent_id}")

    # Resolve or create customer
    customer = app_store.get_customer_by_external_id(
        tenant_id=tenant_uuid,
        channel=channel_type.value,
        external_id=event.external_chat_id,
    )
    if not customer:
        customer = app_store.create_customer(
            tenant_id=tenant_uuid,
            channel=channel_type.value,
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
        channel_type.value,
        external_id=event.external_chat_id,
        phone=customer.phone,
    )
    if existing_suppression:
        app_store.create_audit_log(
            event_type="contact_suppression.inbound_ignored",
            tenant_id=tenant_uuid,
            details={
                "channel": channel_type.value,
                "contact_type": existing_suppression.contact_type,
                "source": f"{channel_type.value}_webhook",
                "suppression_id": str(existing_suppression.id),
                "value": existing_suppression.value,
            },
        )
        return {"status": "ok", "message": "suppressed"}

    try:
        check_billing_limit(tenant_uuid, app_store)
    except HTTPException as e:
        if e.status_code == 402:
            limit_message = (
                "Уведомление: Лимит сообщений для этого ИИ-агента исчерпан. "
                "Пожалуйста, обновите тарифный план в личном кабинете CallForce."
            )
            outbound = OutboundMessage(
                channel=channel_type,
                external_chat_id=event.external_chat_id,
                text=limit_message,
                reply_to_message_id=event.external_message_id,
            )
            await adapter.send_message(outbound)
            return {"status": "error", "message": "Billing limit reached"}
        raise e

    # Process message via Orchestrator
    from app.service_factory import get_agent_orchestrator
    orchestrator = get_agent_orchestrator()

    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        customer_message=event.text,
        channel=channel_type.value,
    )
    
    # If the response is completely empty (e.g., handoff_status is "assigned" so it skips), do not send empty message
    if not orchestrator_result.response_text:
        return {"status": "ok"}
        
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
            channel=channel_type.value,
        )
    else:
        forced_status = auto_reply_decision.forced_status
        forced_resolution_status = auto_reply_decision.forced_resolution_status

    app_store.record_chat_turn_background(
        tenant_id=tenant_uuid,
        agent_id=agent_uuid,
        conversation_id=conversation_uuid,
        channel=channel_type.value,
        customer_text=event.text,
        agent_response_text=response_text,
        customer_id=customer.id if customer else None,
        confidence_score=orchestrator_result.confidence_score,
        forced_status=forced_status,
        forced_resolution_status=forced_resolution_status,
    )

    if orchestrator_result.guardrail_code == "opt_out_requested":
        app_store.record_contact_suppression(
            tenant_uuid,
            channel_type.value,
            "external_id",
            event.external_chat_id,
            reason="opt_out_requested",
            source=f"{channel_type.value}_guardrail",
        )

    if not auto_reply_decision.allowed:
        audit_channel_policy_auto_reply_block(
            app_store,
            tenant_id=tenant_uuid,
            channel=channel_type.value,
            conversation_id=conversation_uuid,
            source=f"{channel_type.value}_webhook",
            policy=channel_policy,
            resolution_status=auto_reply_decision.forced_resolution_status,
            block_reason=auto_reply_decision.block_reason or "automation_mode",
            agent_reply_count=auto_reply_decision.agent_reply_count,
        )
        return {"status": "ok", "message": "channel_policy_auto_reply_blocked"}

    # Send response back via the Adapter
    outbound = OutboundMessage(
        channel=channel_type,
        external_chat_id=event.external_chat_id,
        text=response_text,
        reply_to_message_id=event.external_message_id,
    )
    result = await adapter.send_message(outbound)

    if not result.success:
        return {"status": "error", "message": result.error}

    return {"status": "ok"}
