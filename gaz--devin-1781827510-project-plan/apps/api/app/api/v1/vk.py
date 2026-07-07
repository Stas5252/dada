from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from app.api.v1.webhooks import generic_webhook_handler
from app.channels import ChannelType
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
    tenant_uuid = UUID(tenant_id)
    tenant = app_store.get_tenant(tenant_uuid)
    if not tenant:
        return PlainTextResponse("ok")

    vk_token = tenant.settings.get("vk_group_token", "")
    vk_adapter = get_vk_adapter(group_token=str(vk_token))

    response = await generic_webhook_handler(
        channel_type=ChannelType.vk,
        request=request,
        adapter=vk_adapter,
        settings=settings,
        app_store=app_store,
        tenant_id=tenant_id,
    )
    
    # Generic webhook handler returns Response or dict.
    # If it's a dict, it means success or error (but VK expects PlainTextResponse("ok")).
    if isinstance(response, dict):
        return PlainTextResponse("ok")
    return response
