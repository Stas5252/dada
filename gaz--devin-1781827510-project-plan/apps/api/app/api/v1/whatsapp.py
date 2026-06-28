from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.channels import ChannelType, OutboundMessage
from app.channels.whatsapp_adapter import parse_whatsapp_update
from app.orchestrator import AgentOrchestrator
from app.service_factory import get_whatsapp_adapter
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])


@router.get("/{tenant_id}")
async def whatsapp_webhook_verify(
    tenant_id: str,
    request: Request,
    app_store: AppStore = Depends(get_app_store),
) -> PlainTextResponse:
    """
    Handle Meta/WhatsApp webhook verification (hub.challenge).
    URL format: GET /api/v1/webhooks/whatsapp/{tenant_id}
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        raise HTTPException(status_code=403, detail="Tenant not found")

    wa_verify_token = tenant.settings.get("whatsapp_verify_token", "")

    if mode == "subscribe" and token == wa_verify_token:
        return PlainTextResponse(content=challenge or "")
    
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/{tenant_id}")
async def whatsapp_webhook_receive(
    tenant_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
) -> dict[str, str]:
    """
    Handle incoming WhatsApp messages.
    URL format: POST /api/v1/webhooks/whatsapp/{tenant_id}
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
        return {"status": "ok"}
        
    wa_app_secret = tenant.settings.get("whatsapp_app_secret")
    if not wa_app_secret:
        raise HTTPException(status_code=403, detail="WhatsApp channel not fully configured")
        
    signature = request.headers.get("x-hub-signature-256")
    if signature:
        import hashlib
        import hmac
        body_bytes = await request.body()
        expected_sig = "sha256=" + hmac.new(
            str(wa_app_secret).encode("utf-8"), body_bytes, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            raise HTTPException(status_code=403, detail="Invalid signature")
    elif wa_app_secret and not signature:
        raise HTTPException(status_code=403, detail="Missing signature")
    if not tenant:
        return {"status": "ok"}

    agents = app_store.list_agents(tenant_uuid)
    agent = next((a for a in agents if a.status == "published"), None)
    
    if not agent:
        return {"status": "ok"}

    wa_token = tenant.settings.get("whatsapp_token")
    wa_phone_id = tenant.settings.get("whatsapp_phone_number_id")
    if not isinstance(wa_token, str) or not wa_token or not isinstance(wa_phone_id, str) or not wa_phone_id:
        return {"status": "ok"}

    wa = get_whatsapp_adapter(access_token=wa_token, phone_number_id=wa_phone_id)

    # Parse into normalized MessageEvents
    events = parse_whatsapp_update(update)
    if not events:
        # Ignore unsupported updates (statuses, read receipts, etc)
        return {"status": "ok"}

    for event in events:
        if wa.is_duplicate_update(event.external_message_id):
            continue

        from app.api.v1.dependencies import check_billing_limit
        try:
            check_billing_limit(tenant_uuid, app_store)
        except HTTPException as e:
            if e.status_code == 402:
                limit_message = "Уведомление: Лимит сообщений исчерпан."
                outbound = OutboundMessage(
                    channel=ChannelType.whatsapp,
                    external_chat_id=event.external_chat_id,
                    text=limit_message,
                )
                await wa.send_message(outbound)
                continue
            raise e

        # Map phone number -> stable conversation UUID
        conversation_uuid = uuid5(NAMESPACE_URL, f"wa_chat:{event.external_chat_id}:{agent.id}")

        # Resolve or create customer
        customer = app_store.get_customer_by_external_id(
            tenant_id=tenant_uuid,
            channel="whatsapp",
            external_id=event.external_chat_id,
        )
        if not customer:
            customer = app_store.create_customer(
                tenant_id=tenant_uuid,
                channel="whatsapp",
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
            channel="whatsapp",
        )

        # Record turn
        app_store.record_chat_turn(
            tenant_id=tenant_uuid,
            agent_id=agent.id,
            conversation_id=conversation_uuid,
            channel="whatsapp",
            customer_text=event.text,
            agent_response_text=orchestrator_result.response_text,
            confidence_score=orchestrator_result.confidence_score,
        )

        # Send response back
        outbound = OutboundMessage(
            channel=ChannelType.whatsapp,
            external_chat_id=event.external_chat_id,
            text=orchestrator_result.response_text,
            reply_to_message_id=event.external_message_id,
        )
        await wa.send_message(outbound)

    return {"status": "ok"}
