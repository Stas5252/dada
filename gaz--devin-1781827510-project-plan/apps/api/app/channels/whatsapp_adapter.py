import logging
from typing import Any

import httpx

from app.channels import ChannelType, DeduplicationStore, MessageEvent, OutboundMessage, SendResult

logger = logging.getLogger(__name__)

def parse_whatsapp_update(update: dict[str, Any]) -> list[MessageEvent]:
    """Parse incoming Meta WhatsApp webhook update into normalized MessageEvents."""
    events: list[MessageEvent] = []
    
    if update.get("object") != "whatsapp_business_account":
        return events

    for entry in update.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if "messages" not in value:
                continue

            # A single event can have multiple messages
            for msg in value.get("messages", []):
                msg_id = msg.get("id")
                from_number = msg.get("from")
                
                # Fetch text depending on message type
                text = ""
                msg_type = msg.get("type")
                if msg_type == "text":
                    text_obj = msg.get("text") or {}
                    text = text_obj.get("body", "")
                elif msg_type == "interactive":
                    interactive = msg.get("interactive") or {}
                    button_reply = interactive.get("button_reply") or {}
                    list_reply = interactive.get("list_reply") or {}
                    text = button_reply.get("title", "") or list_reply.get("title", "")

                if not msg_id or not from_number or not text:
                    continue

                # Find sender name in contacts if provided
                sender_name = "WhatsApp User"
                for contact in value.get("contacts", []):
                    if contact.get("wa_id") == from_number:
                        sender_name = contact.get("profile", {}).get("name", sender_name)
                        break

                events.append(MessageEvent(
                    channel=ChannelType.whatsapp,
                    external_chat_id=str(from_number),
                    external_message_id=msg_id,
                    sender_name=sender_name,
                    text=text,
                    raw_payload=msg,
                ))

    return events


class WhatsAppChannelAdapter:
    def __init__(self, access_token: str, phone_number_id: str) -> None:
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_version = "v19.0"
        self._dedup = DeduplicationStore()

    def is_duplicate_update(self, event_id: str) -> bool:
        return self._dedup.is_duplicate(f"wa_{event_id}")

    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send a message via Meta Cloud API."""
        url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": message.external_chat_id,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message.text
            }
        }
        
        # If reply, use context
        if message.reply_to_message_id:
            payload["context"] = {"message_id": message.reply_to_message_id}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                data = response.json()
                
                if "error" in data:
                    logger.error(f"WhatsApp send error: {data['error']}")
                    return SendResult(success=False, error=str(data["error"]))

                messages_info = data.get("messages", [])
                msg_id = messages_info[0].get("id") if messages_info else ""
                
                return SendResult(
                    success=True,
                    external_message_id=msg_id,
                )
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return SendResult(success=False, error=str(e))
