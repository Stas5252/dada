from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, Request

from app.channels import ChannelType, OutboundMessage
from app.channels.vk_adapter import VKChannelAdapter, parse_vk_update
from app.orchestrator import AgentOrchestrator
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/webhooks/vk", tags=["vk"])


@router.post("/{tenant_id}")
async def vk_webhook(
    tenant_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, str] | str:
    """
    Handle incoming VK Community messages.
    URL format: /api/v1/webhooks/vk/{tenant_id}
    """
    try:
        update = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        return "ok"

    # VK Confirmation Challenge
    if update.get("type") == "confirmation":
        vk_confirmation_code = tenant.settings.get("vk_confirmation_code", "")
        if isinstance(vk_confirmation_code, str) and vk_confirmation_code:
            return vk_confirmation_code
        return "ok"

    # Find the default agent for this tenant (VK usually routes to the primary agent)
    # We will just pick the first active agent, or ideally we'd configure a default_agent_id in settings
    agents = app_store.list_agents(tenant_uuid)
    agent = next((a for a in agents if a.status == "published"), None)
    
    if not agent:
        return "ok"

    vk_token = tenant.settings.get("vk_group_token")
    if not isinstance(vk_token, str) or not vk_token:
        return "ok"

    vk = VKChannelAdapter(group_token=vk_token)

    # Parse into normalized MessageEvent
    event = parse_vk_update(update)
    if not event:
        # Ignore unsupported updates
        return "ok"

    if vk.is_duplicate_update(event.external_message_id):
        return "ok"

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
            return "ok"
        raise e

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
        )

    # Run Orchestrator
    orchestrator = AgentOrchestrator(store=app_store, settings=settings)
    orchestrator_result = await orchestrator.process_message(
        tenant_id=tenant_uuid,
        agent_id=agent.id,
        conversation_id=conversation_uuid,
        customer_message=event.text,
        channel="vk",
    )

    # Record turn
    app_store.record_chat_turn(
        tenant_id=tenant_uuid,
        agent_id=agent.id,
        conversation_id=conversation_uuid,
        channel="vk",
        customer_text=event.text,
        agent_response_text=orchestrator_result.response_text,
        confidence_score=orchestrator_result.confidence_score,
    )

    # Send response back to VK
    outbound = OutboundMessage(
        channel=ChannelType.vk,
        external_chat_id=event.external_chat_id,
        text=orchestrator_result.response_text,
        reply_to_message_id=event.external_message_id,
    )
    await vk.send_message(outbound)

    return "ok"
