import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from app.schemas import (
    ChannelAutomationMode,
    ChannelCompliancePolicySettings,
    ChannelPoliciesSettings,
    Conversation,
    ConversationStatus,
    KnowledgeSource,
    Message,
    MessageRole,
)

logger = logging.getLogger(__name__)

CHANNEL_POLICIES_SETTINGS_KEY = "channel_policies"
AUTO_REPLY_LIMIT_REACHED_STATUS = "channel_policy_auto_reply_limit_reached"
OPT_OUT_NOTICE_TEXT = "Reply STOP to opt out of automated messages."

_CHANNEL_FIELD_ALIASES = {
    "web": "web_widget",
    "web_widget": "web_widget",
    "widget": "web_widget",
    "telegram": "telegram",
    "vk": "vk",
    "whatsapp": "whatsapp",
    "voice": "voice",
    "sip": "voice",
    "asterisk": "voice",
    "twilio": "voice",
    "twilio_sms": "voice",
}


class AuditLogWriter(Protocol):
    def create_audit_log(
        self,
        event_type: str,
        user_id: UUID | None = None,
        tenant_id: UUID | None = None,
        ip_address: str | None = None,
        details: dict[str, str] | None = None,
    ) -> object: ...


class ConversationDetailReader(Protocol):
    def get_conversation_detail(
        self,
        tenant_id: UUID,
        conversation_id: UUID,
    ) -> tuple[Conversation, list[Message], list[KnowledgeSource]] | None: ...


@dataclass(frozen=True)
class ChannelAutoReplyDecision:
    allowed: bool
    public_status: str = "ok"
    forced_status: ConversationStatus | None = None
    forced_resolution_status: str | None = None
    block_reason: str | None = None
    agent_reply_count: int | None = None


def channel_policies_from_settings(
    tenant_settings: Mapping[str, object] | None,
) -> ChannelPoliciesSettings:
    if not tenant_settings:
        return ChannelPoliciesSettings()

    raw_policies = tenant_settings.get(CHANNEL_POLICIES_SETTINGS_KEY)
    if isinstance(raw_policies, ChannelPoliciesSettings):
        return raw_policies
    if isinstance(raw_policies, Mapping):
        try:
            return ChannelPoliciesSettings.model_validate(raw_policies)
        except ValidationError as exc:
            logger.warning("Invalid channel policy in tenant settings: %s", exc)

    return ChannelPoliciesSettings()


def channel_policy_for_settings(
    tenant_settings: Mapping[str, object] | None,
    channel: str,
) -> ChannelCompliancePolicySettings:
    policies = channel_policies_from_settings(tenant_settings)
    field_name = _CHANNEL_FIELD_ALIASES.get(channel, "default_policy")
    value = getattr(policies, field_name, None)
    return value if isinstance(value, ChannelCompliancePolicySettings) else policies.default_policy


def should_auto_send_channel_response(policy: ChannelCompliancePolicySettings) -> bool:
    return policy.outbound_enabled and policy.mode == ChannelAutomationMode.autopilot


def channel_policy_resolution_status(policy: ChannelCompliancePolicySettings) -> str:
    if not policy.outbound_enabled:
        return "channel_policy_outbound_disabled"
    if policy.mode == ChannelAutomationMode.draft_only:
        return "channel_policy_draft_only"
    if policy.mode == ChannelAutomationMode.human_approval:
        return "channel_policy_human_approval_required"
    return "resolved"


def channel_policy_public_status(policy: ChannelCompliancePolicySettings) -> str:
    if should_auto_send_channel_response(policy):
        return "ok"
    if not policy.outbound_enabled:
        return "outbound_disabled"
    return policy.mode.value


def channel_policy_forced_state(
    policy: ChannelCompliancePolicySettings,
) -> tuple[ConversationStatus, str]:
    return ConversationStatus.escalated, channel_policy_resolution_status(policy)


def count_agent_auto_replies(
    store: ConversationDetailReader,
    *,
    tenant_id: UUID,
    conversation_id: UUID,
) -> int:
    conversation_detail = store.get_conversation_detail(tenant_id, conversation_id)
    if conversation_detail is None:
        return 0
    _conversation, messages, _sources = conversation_detail
    return sum(1 for message in messages if message.role == MessageRole.agent)


def evaluate_channel_auto_reply_policy(
    store: ConversationDetailReader,
    *,
    tenant_id: UUID,
    conversation_id: UUID,
    policy: ChannelCompliancePolicySettings,
) -> ChannelAutoReplyDecision:
    if not should_auto_send_channel_response(policy):
        forced_status, forced_resolution_status = channel_policy_forced_state(policy)
        return ChannelAutoReplyDecision(
            allowed=False,
            public_status=channel_policy_public_status(policy),
            forced_status=forced_status,
            forced_resolution_status=forced_resolution_status,
            block_reason="automation_mode",
        )

    agent_reply_count = count_agent_auto_replies(
        store,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
    )
    if agent_reply_count >= policy.max_auto_replies_per_conversation:
        return ChannelAutoReplyDecision(
            allowed=False,
            public_status="auto_reply_limit_reached",
            forced_status=ConversationStatus.escalated,
            forced_resolution_status=AUTO_REPLY_LIMIT_REACHED_STATUS,
            block_reason="auto_reply_limit",
            agent_reply_count=agent_reply_count,
        )

    return ChannelAutoReplyDecision(
        allowed=True,
        agent_reply_count=agent_reply_count,
    )


def append_channel_opt_out_notice(
    text: str,
    *,
    policy: ChannelCompliancePolicySettings,
    channel: str,
) -> str:
    if (
        not policy.require_opt_out_notice
        or channel == "voice"
        or not text.strip()
        or OPT_OUT_NOTICE_TEXT.casefold() in text.casefold()
    ):
        return text
    return f"{text.rstrip()}\n\n{OPT_OUT_NOTICE_TEXT}"


def audit_channel_policy_auto_reply_block(
    store: AuditLogWriter,
    *,
    tenant_id: UUID,
    channel: str,
    conversation_id: UUID,
    source: str,
    policy: ChannelCompliancePolicySettings,
    resolution_status: str | None = None,
    block_reason: str = "automation_mode",
    agent_reply_count: int | None = None,
) -> None:
    create_audit_log = store.create_audit_log
    details = {
        "channel": channel,
        "conversation_id": str(conversation_id),
        "mode": policy.mode.value,
        "outbound_enabled": str(policy.outbound_enabled).lower(),
        "resolution_status": resolution_status or channel_policy_resolution_status(policy),
        "source": source,
        "block_reason": block_reason,
        "max_auto_replies_per_conversation": str(policy.max_auto_replies_per_conversation),
    }
    if agent_reply_count is not None:
        details["agent_reply_count"] = str(agent_reply_count)

    create_audit_log(
        tenant_id=tenant_id,
        user_id=None,
        event_type="channel_policy.auto_reply_blocked",
        ip_address=None,
        details=details,
    )


def audit_channel_policy_outbound_block(
    store: AuditLogWriter,
    *,
    tenant_id: UUID,
    channel: str,
    conversation_id: UUID,
    source: str,
    policy: ChannelCompliancePolicySettings,
) -> None:
    create_audit_log = store.create_audit_log
    create_audit_log(
        tenant_id=tenant_id,
        user_id=None,
        event_type="channel_policy.outbound_blocked",
        ip_address=None,
        details={
            "channel": channel,
            "conversation_id": str(conversation_id),
            "mode": policy.mode.value,
            "outbound_enabled": str(policy.outbound_enabled).lower(),
            "source": source,
        },
    )


def audit_channel_policy_consent_block(
    store: AuditLogWriter,
    *,
    tenant_id: UUID,
    channel: str,
    conversation_id: UUID,
    source: str,
    policy: ChannelCompliancePolicySettings,
    contact_type: str | None = None,
    value: str | None = None,
) -> None:
    details = {
        "channel": channel,
        "conversation_id": str(conversation_id),
        "mode": policy.mode.value,
        "outbound_enabled": str(policy.outbound_enabled).lower(),
        "require_contact_consent_for_outbound": str(
            policy.require_contact_consent_for_outbound
        ).lower(),
        "source": source,
    }
    if contact_type:
        details["contact_type"] = contact_type
    if value:
        details["value"] = value

    store.create_audit_log(
        tenant_id=tenant_id,
        user_id=None,
        event_type="channel_policy.consent_required_blocked",
        ip_address=None,
        details=details,
    )
