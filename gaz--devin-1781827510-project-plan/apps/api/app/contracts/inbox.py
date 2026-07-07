from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationTag(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    conversation_id: str
    tag_name: str
    created_at: datetime


class AddTagRequest(BaseModel):
    tag_name: str


class InternalNote(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    conversation_id: str | None
    body: str
    author_user_id: str | None
    created_at: datetime
    updated_at: datetime


class InternalNoteCreate(BaseModel):
    body: str
    author_user_id: str | None = None


class HandoffAssignment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    conversation_id: str
    user_id: str
    status: str
    assigned_at: datetime
    unassigned_at: datetime | None


class AssignConversationRequest(BaseModel):
    user_id: str


class ManualMessageRequest(BaseModel):
    content: str


class InboxConversation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str
    customer_id: str | None
    channel: str
    status: str
    summary: str
    resolution_status: str
    created_at: datetime
    priority: str
    sla_due_at: datetime | None
    handoff_status: str
    assigned_user_id: str | None

    tags: list[str] = Field(default_factory=list)
