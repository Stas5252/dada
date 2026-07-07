from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.api.v1.webhooks import generic_webhook_handler
from app.channels import ChannelType
from app.channels.meta_adapter import MetaChannelAdapter
from app.settings import Settings, get_settings
from app.store_factory import AppStore, get_app_store

router = APIRouter(prefix="/webhooks/meta", tags=["meta"])


@router.post("/{tenant_id}")
async def meta_webhook(
    tenant_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    app_store: AppStore = Depends(get_app_store),
):
    """
    Handle incoming Meta (Instagram/Facebook) messages.
    URL format: POST /api/v1/webhooks/meta/{tenant_id}
    """
    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        return JSONResponse({"status": "ok"})

    access_token = tenant.settings.get("meta_access_token", "")
    page_id = tenant.settings.get("meta_page_id", "")
    meta_adapter = MetaChannelAdapter(access_token=str(access_token), page_id=str(page_id))

    response = await generic_webhook_handler(
        channel_type=ChannelType("instagram") if "instagram" in [e.value for e in ChannelType] else ChannelType.web_widget,
        request=request,
        adapter=meta_adapter,
        settings=settings,
        app_store=app_store,
        tenant_id=tenant_id,
    )
    if isinstance(response, dict):
        return JSONResponse(response)
    return response
