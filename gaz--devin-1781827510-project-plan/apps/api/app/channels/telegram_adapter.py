"""
Production Telegram channel adapter.
Handles real Telegram Bot API for sending/receiving messages.
Falls back to local stub when TELEGRAM_BOT_TOKEN is not set.
"""

import logging
from dataclasses import dataclass, field

import httpx

from app.channels import (
    ChannelType,
    DeduplicationStore,
    MessageEvent,
    OutboundMessage,
    SendResult,
)

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


def parse_telegram_update(update: dict[str, object]) -> MessageEvent | None:
    """Parse a Telegram update JSON into a normalized MessageEvent."""
    msg = update.get("message")
    if not isinstance(msg, dict):
        return None

    chat = msg.get("chat", {})
    if not isinstance(chat, dict):
        return None

    chat_id = chat.get("id")
    text = msg.get("text", "")
    if not chat_id or not text:
        return None

    from_user = msg.get("from", {})
    if not isinstance(from_user, dict):
        from_user = {}

    sender_name_parts: list[str] = []
    first_name = from_user.get("first_name", "")
    last_name = from_user.get("last_name", "")
    if isinstance(first_name, str) and first_name:
        sender_name_parts.append(first_name)
    if isinstance(last_name, str) and last_name:
        sender_name_parts.append(last_name)

    message_id = msg.get("message_id", "")

    return MessageEvent(
        channel=ChannelType.telegram,
        external_chat_id=str(chat_id),
        external_message_id=str(message_id),
        sender_name=" ".join(sender_name_parts) if sender_name_parts else "Unknown",
        text=str(text),
        raw_payload=update,
    )


@dataclass
class TelegramChannelAdapter:
    """
    Production Telegram Bot adapter.
    If bot_token is empty, operates in local stub mode (logs but doesn't send).
    """

    bot_token: str = ""
    dedup: DeduplicationStore = field(default_factory=DeduplicationStore)

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token)

    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send a message via Telegram Bot API."""
        if not self.is_configured:
            logger.info(
                "[Telegram STUB] Would send to chat %s: %s...",
                message.external_chat_id,
                message.text[:100],
            )
            return SendResult(
                success=True,
                external_message_id="stub-" + message.external_chat_id,
            )

        try:
            url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
            payload: dict[str, object] = {
                "chat_id": message.external_chat_id,
                "text": message.text,
                "parse_mode": "Markdown",
            }
            if message.reply_to_message_id:
                payload["reply_to_message_id"] = message.reply_to_message_id

            from app.security import SSRFTransport
            async with httpx.AsyncClient(transport=SSRFTransport(), timeout=10.0) as client:
                response = await client.post(url, json=payload)

            if response.status_code == 200:
                data = response.json()
                result_msg = data.get("result", {})
                return SendResult(
                    success=True,
                    external_message_id=str(result_msg.get("message_id", "")),
                )
            else:
                error_text = response.text[:200]
                logger.error("Telegram API error %d: %s", response.status_code, error_text)
                # Retry without markdown if parsing failed
                if response.status_code == 400 and "parse" in error_text.lower():
                    return await self._send_plain(message)
                return SendResult(success=False, error=error_text)

        except httpx.TimeoutException:
            logger.error("Telegram API timeout")
            return SendResult(success=False, error="Timeout")
        except Exception as e:
            logger.error("Telegram send error: %s", e)
            return SendResult(success=False, error=str(e))

    async def _send_plain(self, message: OutboundMessage) -> SendResult:
        """Retry sending without markdown parsing."""
        try:
            url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
            payload: dict[str, object] = {
                "chat_id": message.external_chat_id,
                "text": message.text,
            }

            from app.security import SSRFTransport
            async with httpx.AsyncClient(transport=SSRFTransport(), timeout=10.0) as client:
                response = await client.post(url, json=payload)

            if response.status_code == 200:
                data = response.json()
                result_msg = data.get("result", {})
                return SendResult(
                    success=True,
                    external_message_id=str(result_msg.get("message_id", "")),
                )
            return SendResult(success=False, error=response.text[:200])
        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def set_webhook(self, webhook_url: str, secret_token: str | None = None) -> bool:
        """Register webhook URL with Telegram Bot API."""
        if not self.is_configured:
            logger.info("[Telegram STUB] Would set webhook to: %s", webhook_url)
            return True

        try:
            url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/setWebhook"
            payload = {"url": webhook_url}
            if secret_token:
                payload["secret_token"] = secret_token
            from app.security import SSRFTransport
            async with httpx.AsyncClient(transport=SSRFTransport(), timeout=10.0) as client:
                response = await client.post(url, json=payload)
            success = response.status_code == 200
            if success:
                logger.info("Telegram webhook set to: %s", webhook_url)
            else:
                logger.error("Failed to set Telegram webhook: %s", response.text)
            return success
        except Exception as e:
            logger.error("Telegram setWebhook error: %s", e)
            return False

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.telegram

    def parse_update(self, payload: dict[str, object]) -> MessageEvent | None:
        return parse_telegram_update(payload)

    async def verify_request(self, request: httpx.Request | getattr(__import__('fastapi'), 'Request'), agent, settings) -> getattr(__import__('fastapi'), 'Response') | None:
        from fastapi import HTTPException
        from app.encryption import decrypt_token
        
        decrypted_token = decrypt_token(agent.telegram_bot_token, settings.access_token_secret)
        if not decrypted_token:
            from fastapi.responses import JSONResponse
            return JSONResponse({"status": "error", "message": "Failed to decrypt Telegram bot token"}, status_code=400)
            
        secret_token_header = request.headers.get("x-telegram-bot-api-secret-token")
        import hashlib
        expected_secret = hashlib.sha256(decrypted_token.encode("utf-8")).hexdigest()
        if secret_token_header != expected_secret:
            raise HTTPException(status_code=403, detail="Invalid secret token")
            
        return None

    def is_duplicate_update(self, payload: dict[str, object]) -> bool:
        """Check if we've already processed this Telegram update."""
        update_id = str(payload.get("update_id", ""))
        if not update_id:
            return False
        return self.dedup.is_duplicate(f"tg-update:{update_id}")
