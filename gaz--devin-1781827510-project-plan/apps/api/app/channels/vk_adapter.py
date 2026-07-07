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

    def is_duplicate_update(self, event_id: str) -> bool:
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
            async with httpx.AsyncClient() as client:
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
