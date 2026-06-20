from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from app.contracts.masking import mask_tenant_payload
from app.contracts.types import JsonValue
from app.rbac import Role


class AuditResource(StrEnum):
    auth = "auth"
    agent = "agent"
    knowledge = "knowledge"
    chat = "chat"


class AuditAction(StrEnum):
    AUTH_REGISTER = "auth.register"
    AUTH_LOGIN = "auth.login"
    AUTH_REFRESH = "auth.refresh"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_VERIFY = "auth.token_verify"
    AGENT_LIST = "agent.list"
    AGENT_CREATE = "agent.create"
    AGENT_PUBLISH = "agent.publish"
    KNOWLEDGE_SOURCE_LIST = "knowledge.source_list"
    KNOWLEDGE_SOURCE_CREATE = "knowledge.source_create"
    CHAT_CONVERSATION_LIST = "chat.conversation_list"
    CHAT_CONVERSATION_DETAIL = "chat.conversation_detail"
    CHAT_MOCK = "chat.mock"


ACTION_RESOURCES: dict[AuditAction, AuditResource] = {
    AuditAction.AUTH_REGISTER: AuditResource.auth,
    AuditAction.AUTH_LOGIN: AuditResource.auth,
    AuditAction.AUTH_REFRESH: AuditResource.auth,
    AuditAction.AUTH_LOGOUT: AuditResource.auth,
    AuditAction.AUTH_TOKEN_VERIFY: AuditResource.auth,
    AuditAction.AGENT_LIST: AuditResource.agent,
    AuditAction.AGENT_CREATE: AuditResource.agent,
    AuditAction.AGENT_PUBLISH: AuditResource.agent,
    AuditAction.KNOWLEDGE_SOURCE_LIST: AuditResource.knowledge,
    AuditAction.KNOWLEDGE_SOURCE_CREATE: AuditResource.knowledge,
    AuditAction.CHAT_CONVERSATION_LIST: AuditResource.chat,
    AuditAction.CHAT_CONVERSATION_DETAIL: AuditResource.chat,
    AuditAction.CHAT_MOCK: AuditResource.chat,
}


class AuditEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    actor_role: Role | None = None
    resource: AuditResource
    action: AuditAction
    outcome: Literal["success", "failure", "denied"]
    masked_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_action_resource(self) -> "AuditEvent":
        if ACTION_RESOURCES[self.action] != self.resource:
            raise ValueError("audit action does not match resource")
        return self


def action_resource(action: AuditAction) -> AuditResource:
    return ACTION_RESOURCES[action]


def build_audit_event(
    *,
    action: AuditAction,
    outcome: Literal["success", "failure", "denied"],
    metadata: dict[str, JsonValue],
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    actor_role: Role | None = None,
) -> AuditEvent:
    mask_tenant_id = str(tenant_id) if tenant_id is not None else ""
    return AuditEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        actor_role=actor_role,
        resource=action_resource(action),
        action=action,
        outcome=outcome,
        masked_metadata=mask_tenant_payload(metadata, tenant_id=mask_tenant_id),
    )
