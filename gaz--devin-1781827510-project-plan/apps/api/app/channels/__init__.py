"""
Base channel adapter interface.
All channel adapters (Telegram, web widget, WhatsApp, VK) implement this interface.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChannelType(StrEnum):
    telegram = "telegram"
    web_widget = "web_widget"
    whatsapp = "whatsapp"
    vk = "vk"
    sip = "sip"


class MessageEvent(BaseModel):
    """Normalized inbound message from any channel."""

    id: UUID = Field(default_factory=uuid4)
    channel: ChannelType
    external_chat_id: str = Field(min_length=1)
    external_message_id: str = ""
    sender_name: str = ""
    text: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw_payload: dict[str, object] = Field(default_factory=dict)


class OutboundMessage(BaseModel):
    """Normalized outbound message to any channel."""

    channel: ChannelType
    external_chat_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=4096)
    reply_to_message_id: str = ""


class SendResult(BaseModel):
    """Result of sending a message via a channel."""

    success: bool
    external_message_id: str = ""
    duplicate: bool = False
    error: str = ""


@dataclass
class DeduplicationStore:
    """Simple in-memory deduplication for webhook idempotency."""

    seen_ids: dict[str, datetime] = field(default_factory=dict)
    max_size: int = 10000

    def is_duplicate(self, key: str) -> bool:
        if key in self.seen_ids:
            return True
        # Clean up if too large
        if len(self.seen_ids) > self.max_size:
            cutoff = sorted(self.seen_ids.values())[len(self.seen_ids) // 2]
            self.seen_ids = {k: v for k, v in self.seen_ids.items() if v > cutoff}
        self.seen_ids[key] = datetime.now(UTC)
        return False


from typing import Protocol, runtime_checkable
from fastapi import Request, Response
from app.schemas import Agent
from app.settings import Settings

@runtime_checkable
class ChannelAdapter(Protocol):
    """Generic interface for channel adapters."""

    @property
    def is_configured(self) -> bool:
        ...

    async def send_message(self, message: OutboundMessage) -> SendResult:
        ...

    def is_duplicate_update(self, update_id: str) -> bool:
        ...

    def parse_update(self, payload: dict[str, object]) -> MessageEvent | None:
        ...

    async def verify_request(self, request: Request, agent: Agent, settings: Settings) -> Response | None:
        """
        Verify the incoming webhook request (e.g., validate signatures).
        Return a Response object to short-circuit (e.g., for webhook verification challenges like VK/Meta),
        or None to continue processing.
        """
        ...
