import logging
from typing import Any

import httpx

from app.channels import ChannelType, DeduplicationStore, MessageEvent, OutboundMessage, SendResult

logger = logging.getLogger(__name__)

class MetaChannelAdapter:
    """Stub adapter for Meta (Instagram/Facebook) Graph API integration."""
    
    def __init__(self, access_token: str, page_id: str) -> None:
        self.access_token = access_token
        self.page_id = page_id
        self._dedup = DeduplicationStore()

    @property
    def channel_type(self) -> ChannelType:
        # We need to add instagram to ChannelType enum if we want to use it.
        return ChannelType("instagram") if "instagram" in [e.value for e in ChannelType] else ChannelType.web_widget

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token and self.page_id)

    def parse_update(self, payload: dict[str, Any]) -> MessageEvent | None:
        # Meta webhook parsing logic goes here
        # Return None for now since it's a stub
        return None

    async def verify_request(self, request: httpx.Request | getattr(__import__('fastapi'), 'Request'), agent, settings) -> getattr(__import__('fastapi'), 'Response') | None:
        # Meta webhook verification logic (similar to WhatsApp hub.challenge) goes here
        return None

    def is_duplicate_update(self, payload: dict[str, object]) -> bool:
        # Extract Meta message ID
        return False

    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send a message via Meta API."""
        if not self.is_configured:
            return SendResult(success=True, external_message_id="stub-meta")
            
        logger.info("[Meta STUB] Sending message to %s: %s", message.external_chat_id, message.text)
        return SendResult(success=True, external_message_id="stub-meta")
