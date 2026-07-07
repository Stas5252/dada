import logging
import secrets
from typing import Any

import httpx

from app.channels import ChannelType, DeduplicationStore, MessageEvent, OutboundMessage, SendResult

logger = logging.getLogger(__name__)

def parse_vk_update(update: dict[str, Any]) -> MessageEvent | None:
    """Parse incoming VK webhook update into our normalized MessageEvent."""
    if update.get("type") != "message_new":
        return None

    obj = update.get("object", {})
    message = obj.get("message", {})
    
    # In VK, peer_id is the chat identifier.
    # from_id is the user identifier.
    peer_id = message.get("peer_id")
    text = message.get("text", "")
    message_id = str(message.get("conversation_message_id", message.get("id", "")))
    
    if not peer_id or not text:
        return None

    return MessageEvent(
        channel=ChannelType.vk,
        external_chat_id=str(peer_id),
        external_message_id=message_id,
        sender_name="VK User", # In real prod, fetch via users.get if needed
        text=text,
        raw_payload=update,
    )


class VKChannelAdapter:
    def __init__(self, group_token: str):
        self.group_token = group_token
        self.api_version = "5.199"
        self._dedup = DeduplicationStore()

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.vk

    @property
    def is_configured(self) -> bool:
        return bool(self.group_token)

    def parse_update(self, payload: dict[str, Any]) -> MessageEvent | None:
        return parse_vk_update(payload)

    async def verify_request(self, request: httpx.Request | getattr(__import__('fastapi'), 'Request'), agent, settings) -> getattr(__import__('fastapi'), 'Response') | None:
        from fastapi import HTTPException
        from fastapi.responses import PlainTextResponse
        from app.store_factory import get_app_store
        
        store = get_app_store()
        try:
            tenant_id = request.url.path.strip("/").split("/")[-1]
            tenant = store.get_tenant(tenant_id)
        except Exception:
            return None
            
        if not tenant:
            return None

        try:
            update = await request.json()
        except Exception:
            return None
            
        vk_secret_key = tenant.settings.get("vk_secret_key")
        
        if update.get("type") == "confirmation":
            return PlainTextResponse(str(tenant.settings.get("vk_confirmation_code", "")))
        if vk_secret_key and update.get("secret") != vk_secret_key:
            raise HTTPException(status_code=403, detail="Invalid VK secret key")
            if isinstance(vk_confirmation_code, str) and vk_confirmation_code:
                return PlainTextResponse(vk_confirmation_code)
            return PlainTextResponse("ok")
            
        return None

    def is_duplicate_update(self, payload: dict[str, object]) -> bool:
        """Check if we've already processed this VK update."""
        obj = payload.get("object", {})
        if not isinstance(obj, dict):
            return False
        message = obj.get("message", {})
        if not isinstance(message, dict):
            return False
        event_id = str(message.get("conversation_message_id", message.get("id", "")))
        if not event_id:
            return False
        return self._dedup.is_duplicate(f"vk_{event_id}")

    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send a message via VK API."""
        url = "https://api.vk.com/method/messages.send"
        params = {
            "access_token": self.group_token,
            "v": self.api_version,
            "peer_id": message.external_chat_id,
            "message": message.text,
            "random_id": secrets.randbelow(2**31 - 1) + 1,
        }
        
        # If reply_to_message_id is present, we could add reply_to.
        # But VK uses `forward` or `reply_to` with specific formats. 
        # For simplicity, we just send standard text message.

        try:
            from app.security import SSRFTransport
            async with httpx.AsyncClient(transport=SSRFTransport()) as client:
                response = await client.post(url, data=params, timeout=10.0)
                data = response.json()
                
                if "error" in data:
                    logger.error(f"VK send error: {data['error']}")
                    return SendResult(success=False, error=str(data["error"]))

                return SendResult(
                    success=True,
                    external_message_id=str(data.get("response", "")),
                )
        except Exception as e:
            logger.error(f"Failed to send VK message: {e}")
            return SendResult(success=False, error=str(e))
