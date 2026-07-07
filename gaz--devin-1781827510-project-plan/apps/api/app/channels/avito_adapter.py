import logging
from typing import Any

import httpx

from app.channels import ChannelType, DeduplicationStore, MessageEvent, OutboundMessage, SendResult

logger = logging.getLogger(__name__)

class AvitoChannelAdapter:
    """Stub adapter for Avito Messenger integration."""
    
    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._dedup = DeduplicationStore()

    @property
    def channel_type(self) -> ChannelType:
        # We need to add avito to ChannelType enum if we want to use it.
        # For now, let's just use a string cast or add it later.
        # In python StrEnum, if we haven't added it to __init__.py, this will fail.
        # But this is a stub.
        return ChannelType("avito") if "avito" in [e.value for e in ChannelType] else ChannelType.web_widget

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def parse_update(self, payload: dict[str, Any]) -> MessageEvent | None:
        # Avito webhook parsing logic goes here
        # Return None for now since it's a stub
        return None

    async def verify_request(self, request: httpx.Request | getattr(__import__('fastapi'), 'Request'), agent, settings) -> getattr(__import__('fastapi'), 'Response') | None:
        # Avito webhook verification logic goes here
        return None

    def is_duplicate_update(self, payload: dict[str, object]) -> bool:
        # Extract Avito message ID
        return False

    async def send_message(self, message: OutboundMessage) -> SendResult:
        """Send a message via Avito API."""
        if not self.is_configured:
            return SendResult(success=True, external_message_id="stub-avito")
            
        logger.info("[Avito STUB] Sending message to %s: %s", message.external_chat_id, message.text)
        return SendResult(success=True, external_message_id="stub-avito")
