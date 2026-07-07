from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.v1.webhooks import generic_webhook_handler
from app.channels import ChannelType
from app.service_factory import get_whatsapp_adapter
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])


@router.get("/{tenant_id}")
async def whatsapp_webhook_verify(
    tenant_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
):
    """
    Handle Meta/WhatsApp webhook verification (hub.challenge).
    URL format: GET /api/v1/webhooks/whatsapp/{tenant_id}
    """
    return await _whatsapp_webhook(tenant_id, request, settings, app_store)


@router.post("/{tenant_id}")
async def whatsapp_webhook_receive(
    tenant_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
):
    """
    Handle incoming WhatsApp messages.
    URL format: POST /api/v1/webhooks/whatsapp/{tenant_id}
    """
    response = await _whatsapp_webhook(tenant_id, request, settings, app_store)
    if isinstance(response, dict):
        return JSONResponse(response)
    return response


async def _whatsapp_webhook(
    tenant_id: str,
    request: Request,
    settings: Settings,
    app_store: AppStore,
):
    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        return JSONResponse({"status": "ok"})

    wa_token = tenant.settings.get("whatsapp_token", "")
    wa_phone_id = tenant.settings.get("whatsapp_phone_number_id", "")
    wa_adapter = get_whatsapp_adapter(access_token=str(wa_token), phone_number_id=str(wa_phone_id))

    response = await generic_webhook_handler(
        channel_type=ChannelType.whatsapp,
        request=request,
        adapter=wa_adapter,
        settings=settings,
        app_store=app_store,
        tenant_id=tenant_id,
    )
    return response
