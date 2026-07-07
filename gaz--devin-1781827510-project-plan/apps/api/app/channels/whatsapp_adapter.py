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

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.whatsapp

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token and self.phone_number_id)

    def parse_update(self, payload: dict[str, Any]) -> MessageEvent | None:
        events = parse_whatsapp_update(payload)
        # WhatsApp webhooks can contain multiple messages in a batch.
        # For simplicity in the generic pipeline, we return the first event.
        # Ideally, the generic pipeline should handle list[MessageEvent], but 
        # we can just return the first one since usually there's only one per webhook.
        return events[0] if events else None

    async def verify_request(self, request: httpx.Request | getattr(__import__('fastapi'), 'Request'), agent, settings) -> getattr(__import__('fastapi'), 'Response') | None:
        from fastapi import HTTPException
        from fastapi.responses import PlainTextResponse
        from app.store_factory import get_app_store

        store = get_app_store()
        # Parse tenant_id from url since agent can be None
        try:
            tenant_id = request.url.path.strip("/").split("/")[-1]
            tenant = store.get_tenant(tenant_id)
        except Exception:
            return None
        
        if not tenant:
            return None

        # Handle GET Verification
        if request.method == "GET":
            mode = request.query_params.get("hub.mode")
            token = request.query_params.get("hub.verify_token")
            challenge = request.query_params.get("hub.challenge")

            wa_verify_token = tenant.settings.get("whatsapp_verify_token", "")

            if mode == "subscribe" and token == wa_verify_token:
                return PlainTextResponse(content=challenge or "")
            raise HTTPException(status_code=403, detail="Verification failed")

        # Handle POST payload validation
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
            
        return None

    def is_duplicate_update(self, payload: dict[str, object]) -> bool:
        """Check if we've already processed this WA update."""
        # Fast way to get first message ID
        events = parse_whatsapp_update(payload)
        if not events:
            return False
        return self._dedup.is_duplicate(f"wa_{events[0].external_message_id}")

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
