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
                f"[Telegram STUB] Would send to chat {message.external_chat_id}: "
                f"{message.text[:100]}..."
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

            async with httpx.AsyncClient(timeout=10.0) as client:
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
                logger.error(f"Telegram API error {response.status_code}: {error_text}")
                # Retry without markdown if parsing failed
                if response.status_code == 400 and "parse" in error_text.lower():
                    return await self._send_plain(message)
                return SendResult(success=False, error=error_text)

        except httpx.TimeoutException:
            logger.error("Telegram API timeout")
            return SendResult(success=False, error="Timeout")
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return SendResult(success=False, error=str(e))

    async def _send_plain(self, message: OutboundMessage) -> SendResult:
        """Retry sending without markdown parsing."""
        try:
            url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
            payload: dict[str, object] = {
                "chat_id": message.external_chat_id,
                "text": message.text,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
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

    async def set_webhook(self, webhook_url: str) -> bool:
        """Register webhook URL with Telegram Bot API."""
        if not self.is_configured:
            logger.info(f"[Telegram STUB] Would set webhook to: {webhook_url}")
            return True

        try:
            url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/setWebhook"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json={"url": webhook_url})
            success = response.status_code == 200
            if success:
                logger.info(f"Telegram webhook set to: {webhook_url}")
            else:
                logger.error(f"Failed to set Telegram webhook: {response.text}")
            return success
        except Exception as e:
            logger.error(f"Telegram setWebhook error: {e}")
            return False

    def is_duplicate_update(self, update_id: str) -> bool:
        """Check if we've already processed this Telegram update."""
        return self.dedup.is_duplicate(f"tg-update:{update_id}")
