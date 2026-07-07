from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.v1.webhooks import generic_webhook_handler
from app.channels import ChannelType
from app.channels.avito_adapter import AvitoChannelAdapter
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/webhooks/avito", tags=["avito"])


@router.post("/{tenant_id}")
async def avito_webhook(
    tenant_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
):
    """
    Handle incoming Avito messages.
    URL format: POST /api/v1/webhooks/avito/{tenant_id}
    """
    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        return JSONResponse({"status": "ok"})

    client_id = tenant.settings.get("avito_client_id", "")
    client_secret = tenant.settings.get("avito_client_secret", "")
    avito_adapter = AvitoChannelAdapter(client_id=str(client_id), client_secret=str(client_secret))

    response = await generic_webhook_handler(
        channel_type=ChannelType("avito") if "avito" in [e.value for e in ChannelType] else ChannelType.web_widget,
        request=request,
        adapter=avito_adapter,
        settings=settings,
        app_store=app_store,
        tenant_id=tenant_id,
    )
    if isinstance(response, dict):
        return JSONResponse(response)
    return response
