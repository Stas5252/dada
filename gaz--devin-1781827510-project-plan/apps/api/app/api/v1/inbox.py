from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.auth import get_current_user
from app.contracts.inbox import (
    AddTagRequest,
    AssignConversationRequest,
    ConversationTag,
    InboxConversation,
    InternalNote,
    InternalNoteCreate,
    ManualMessageRequest,
)
from app.schemas import User
from app.store_factory import AppStore, get_app_store

router = APIRouter()


@router.get("/conversations", response_model=list[InboxConversation])
def list_inbox_conversations(
    handoff_status: str | None = None,
    assigned_user_id: str | None = None,
    user: User = Depends(get_current_user),
    store: AppStore = Depends(get_app_store),
) -> list[InboxConversation]:
    """List conversations for the human handoff inbox."""
    return store.list_inbox_conversations(
        tenant_id=user.tenant_id,
        handoff_status=handoff_status,
        assigned_user_id=assigned_user_id,
    )


@router.post("/conversations/{conversation_id}/assign", response_model=InboxConversation)
def assign_conversation(
    conversation_id: str,
    payload: AssignConversationRequest,
    user: User = Depends(get_current_user),
    store: AppStore = Depends(get_app_store),
) -> InboxConversation:
    """Assign a conversation to a human manager."""
    conv = store.assign_conversation(
        tenant_id=user.tenant_id,
        conversation_id=conversation_id,
        user_id=payload.user_id,
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/conversations/{conversation_id}/return", response_model=InboxConversation)
def return_conversation_to_ai(
    conversation_id: str,
    user: User = Depends(get_current_user),
    store: AppStore = Depends(get_app_store),
) -> InboxConversation:
    """Return a conversation to AI handling."""
    conv = store.return_conversation_to_ai(
        tenant_id=user.tenant_id,
        conversation_id=conversation_id,
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/conversations/{conversation_id}/tags", response_model=ConversationTag)
def add_conversation_tag(
    conversation_id: str,
    payload: AddTagRequest,
    user: User = Depends(get_current_user),
    store: AppStore = Depends(get_app_store),
) -> ConversationTag:
    """Add a tag to a conversation."""
    tag = store.add_conversation_tag(
        tenant_id=user.tenant_id,
        conversation_id=conversation_id,
        tag_name=payload.tag_name,
    )
    if not tag:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return tag


@router.delete("/conversations/{conversation_id}/tags/{tag_name}", status_code=204)
def remove_conversation_tag(
    conversation_id: str,
    tag_name: str,
    user: User = Depends(get_current_user),
    store: AppStore = Depends(get_app_store),
) -> None:
    """Remove a tag from a conversation."""
    success = store.remove_conversation_tag(
        tenant_id=user.tenant_id,
        conversation_id=conversation_id,
        tag_name=tag_name,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Tag or conversation not found")


@router.post("/conversations/{conversation_id}/notes", response_model=InternalNote)
def add_internal_note(
    conversation_id: str,
    payload: InternalNoteCreate,
    user: User = Depends(get_current_user),
    store: AppStore = Depends(get_app_store),
) -> InternalNote:
    """Add an internal note to a conversation."""
    note = store.add_internal_note(
        tenant_id=user.tenant_id,
        conversation_id=conversation_id,
        body=payload.body,
        author_user_id=payload.author_user_id or str(user.id),
    )
    if not note:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return note
