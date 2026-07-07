import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from app.schemas import ConversationStatus, GuardrailPolicySettings

logger = logging.getLogger(__name__)

GuardRailAction = Literal["allow", "block", "escalate", "opt_out"]
GUARDRAIL_POLICY_SETTINGS_KEY = "guardrail_policy"


class GuardRailError(Exception):
    pass


def guardrail_policy_from_settings(
    tenant_settings: Mapping[str, object] | None,
) -> GuardrailPolicySettings:
    if not tenant_settings:
        return GuardrailPolicySettings()

    raw_policy = tenant_settings.get(GUARDRAIL_POLICY_SETTINGS_KEY)
    if isinstance(raw_policy, GuardrailPolicySettings):
        return raw_policy
    if isinstance(raw_policy, Mapping):
        try:
            return GuardrailPolicySettings.model_validate(raw_policy)
        except ValidationError as exc:
            logger.warning("Invalid guardrail policy in tenant settings: %s", exc)

    return GuardrailPolicySettings()


@dataclass(frozen=True)
class GuardRailDecision:
    code: str
    action: GuardRailAction
    message: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    forced_status: ConversationStatus | None = ConversationStatus.escalated
    forced_resolution_status: str | None = None

    def audit_details(
        self,
        *,
        agent_id: str,
        conversation_id: str,
        channel: str,
        sample: str,
    ) -> dict[str, str]:
        return {
            "action": self.action,
            "agent_id": agent_id,
            "channel": channel,
            "code": self.code,
            "conversation_id": conversation_id,
            "sample": sample[:500],
            "severity": self.severity,
        }


class RuntimeGuardRails:
    """Runtime safety checks for inbound messages, LLM output and tool calls."""

    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
        re.compile(r"system\s+override", re.IGNORECASE),
        re.compile(r"you\s+are\s+now", re.IGNORECASE),
        re.compile(r"reveal\s+(your\s+)?(system|developer)\s+prompt", re.IGNORECASE),
        re.compile(r"show\s+(me\s+)?(your\s+)?(system|developer)\s+prompt", re.IGNORECASE),
        re.compile(r"забудь\s+все", re.IGNORECASE),
        re.compile(r"забудь\s+предыдущие", re.IGNORECASE),
        re.compile(r"теперь\s+ты", re.IGNORECASE),
        re.compile(r"покажи\s+(свой\s+)?(системный|developer)\s+промпт", re.IGNORECASE),
    ]

    OPT_OUT_PATTERNS = [
        re.compile(r"\bstop\b", re.IGNORECASE),
        re.compile(r"\bunsubscribe\b", re.IGNORECASE),
        re.compile(r"\bотпис", re.IGNORECASE),
        re.compile(r"не\s+(пишите|звоните|отправляйте|беспокойте)", re.IGNORECASE),
        re.compile(r"больше\s+не\s+(пишите|звоните|отправляйте|беспокойте)", re.IGNORECASE),
        re.compile(r"удалите\s+(мой\s+)?(номер|телефон|контакт)", re.IGNORECASE),
        re.compile(r"уберите\s+(мой\s+)?(номер|телефон|контакт)", re.IGNORECASE),
    ]

    HUMAN_HANDOFF_PATTERNS = [
        re.compile(r"\bоператор[ау]?\b", re.IGNORECASE),
        re.compile(r"\bменеджер[ау]?\b", re.IGNORECASE),
        re.compile(r"\bчеловек[ау]?\b", re.IGNORECASE),
        re.compile(r"жив(ой|ого)\s+(оператор|человек|специалист)", re.IGNORECASE),
        re.compile(r"\bжалоб", re.IGNORECASE),
        re.compile(r"\bпретензи", re.IGNORECASE),
        re.compile(r"\bруководител", re.IGNORECASE),
    ]

    REGULATED_TOPIC_PATTERNS = [
        re.compile(r"\b(диагноз|лекарств|лечение|операци[яю]|анализы)\b", re.IGNORECASE),
        re.compile(r"\b(юрист|суд|иск|договор|штраф|законно|налог)\b", re.IGNORECASE),
        re.compile(r"\b(кредит|займ|ипотек|инвестиц|страховк)\b", re.IGNORECASE),
        re.compile(r"\b(паспорт|снилс|инн|карта|cvv|пароль)\b", re.IGNORECASE),
    ]

    UNACCEPTABLE_PATTERNS = [
        re.compile(r"\b(хуй|пизд|еба|бля|сука|мудак|хер)\w*\b", re.IGNORECASE),
    ]

    SECRET_LEAK_PATTERNS = [
        re.compile(r"(system|developer)\s+prompt", re.IGNORECASE),
        re.compile(r"SAFETY POLICY", re.IGNORECASE),
        re.compile(r"AGENT SPECIFIC PROMPT", re.IGNORECASE),
        re.compile(r"ACCESS_TOKEN_SECRET|database_password|api[_-]?key", re.IGNORECASE),
        re.compile(r"(системн\w+|developer)\s+промпт", re.IGNORECASE),
    ]

    PROHIBITED_OUTBOUND_PATTERNS = [
        re.compile(r"\b100\s*%\s*(гарант|результат|одобрен)", re.IGNORECASE),
        re.compile(r"\bгарантир(ую|уем)\b", re.IGNORECASE),
        re.compile(r"\bточно\s+(вылечим|одобрим|выиграем)\b", re.IGNORECASE),
        re.compile(r"\bможно\s+не\s+читать\s+договор\b", re.IGNORECASE),
    ]

    EXPLICIT_CONFIRMATION_PATTERNS = [
        re.compile(r"\b(да|верно|подтверждаю|согласен|согласна|оформляйте)\b", re.IGNORECASE),
        re.compile(r"\b(ok|okay|yes|confirm|confirmed)\b", re.IGNORECASE),
    ]

    ALLOWED_TOOL_NAMES = {
        "add_to_cart",
        "checkout_cart",
        "confirm_order",
        "escalate_to_human",
        "remove_from_cart",
    }

    @classmethod
    def evaluate_inbound_message(
        cls,
        message: str,
        policy: GuardrailPolicySettings | None = None,
    ) -> GuardRailDecision | None:
        """Return a runtime decision for a customer message, or None when allowed."""
        resolved_policy = policy or GuardrailPolicySettings()

        if resolved_policy.opt_out_enabled and cls._matches(cls.OPT_OUT_PATTERNS, message):
            logger.warning("GuardRail detected opt-out intent.")
            return GuardRailDecision(
                code="opt_out_requested",
                action="opt_out",
                severity="high",
                forced_resolution_status="opt_out_requested",
                message=(
                    "Понял: больше не буду отправлять вам сообщения. "
                    "Передал запрос команде, чтобы зафиксировать отказ от коммуникаций."
                ),
            )

        if not resolved_policy.enabled:
            return None

        if (
            resolved_policy.prompt_injection_block_enabled
            and cls._matches(cls.INJECTION_PATTERNS, message)
        ):
            logger.warning("GuardRail blocked inbound prompt-injection pattern.")
            return GuardRailDecision(
                code="prompt_injection",
                action="block",
                severity="high",
                forced_resolution_status="guardrail_blocked_prompt_injection",
                message=(
                    "Я не могу выполнять команды, которые меняют правила работы системы. "
                    "Напишите, пожалуйста, обычный вопрос по вашему обращению."
                ),
            )

        if (
            resolved_policy.toxicity_escalation_enabled
            and cls._matches(cls.UNACCEPTABLE_PATTERNS, message)
        ):
            logger.warning("GuardRail detected severe toxicity in inbound message.")
            return GuardRailDecision(
                code="toxic_inbound",
                action="escalate",
                severity="medium",
                forced_resolution_status="guardrail_escalated_toxicity",
                message=(
                    "Давайте продолжим уважительно. Я передаю диалог оператору, "
                    "чтобы вам помогли без лишнего напряжения."
                ),
            )

        if (
            resolved_policy.human_handoff_enabled
            and cls._matches(cls.HUMAN_HANDOFF_PATTERNS, message)
        ):
            logger.info("GuardRail detected explicit human handoff intent.")
            return GuardRailDecision(
                code="human_requested",
                action="escalate",
                severity="medium",
                forced_resolution_status="human_requested",
                message="Передаю вас живому специалисту. Пожалуйста, подождите.",
            )

        if resolved_policy.regulated_topics_enabled and cls._matches(
            cls.REGULATED_TOPIC_PATTERNS,
            message,
        ):
            logger.info("GuardRail detected regulated or sensitive topic.")
            return GuardRailDecision(
                code="regulated_topic",
                action="escalate",
                severity="high",
                forced_resolution_status="guardrail_escalated_regulated_topic",
                message=(
                    "Этот вопрос лучше проверить со специалистом. Передаю диалог оператору, "
                    "чтобы не дать неточную или рискованную рекомендацию."
                ),
            )

        if resolved_policy.regulated_topics_enabled and cls._matches_phrases(
            resolved_policy.custom_regulated_terms,
            message,
        ):
            logger.info("GuardRail detected tenant custom regulated phrase.")
            return GuardRailDecision(
                code="custom_regulated_topic",
                action="escalate",
                severity="high",
                forced_resolution_status="guardrail_escalated_custom_regulated_topic",
                message=(
                    "Этот вопрос лучше проверить со специалистом. Передаю диалог оператору, "
                    "чтобы команда дала точный и безопасный ответ."
                ),
            )

        return None

    @classmethod
    def evaluate_outbound_message(
        cls,
        message: str,
        policy: GuardrailPolicySettings | None = None,
    ) -> GuardRailDecision | None:
        """Return a runtime decision for an agent response, or None when allowed."""
        resolved_policy = policy or GuardrailPolicySettings()
        if not resolved_policy.enabled or not resolved_policy.outbound_safety_enabled:
            return None

        if (
            resolved_policy.toxicity_escalation_enabled
            and cls._matches(cls.UNACCEPTABLE_PATTERNS, message)
        ):
            logger.warning("GuardRail blocked outbound message due to unacceptable content.")
            return GuardRailDecision(
                code="toxic_outbound",
                action="escalate",
                severity="high",
                forced_resolution_status="guardrail_blocked_toxic_outbound",
                message=(
                    "Извините, я не могу безопасно ответить автоматически. "
                    "Передаю диалог оператору."
                ),
            )

        if cls._matches(cls.SECRET_LEAK_PATTERNS, message):
            logger.warning("GuardRail blocked outbound message due to possible secret leakage.")
            return GuardRailDecision(
                code="secret_leak_attempt",
                action="escalate",
                severity="critical",
                forced_resolution_status="guardrail_blocked_secret_leak",
                message=(
                    "Я не могу раскрывать внутренние инструкции или технические данные. "
                    "Передаю диалог оператору."
                ),
            )

        if cls._matches(cls.PROHIBITED_OUTBOUND_PATTERNS, message):
            logger.warning("GuardRail blocked outbound message due to prohibited claim.")
            return GuardRailDecision(
                code="prohibited_claim",
                action="escalate",
                severity="high",
                forced_resolution_status="guardrail_blocked_prohibited_claim",
                message=(
                    "Я не могу автоматически давать такие гарантии. "
                    "Передаю вопрос специалисту для точного ответа."
                ),
            )

        if cls._matches_phrases(resolved_policy.custom_prohibited_claims, message):
            logger.warning("GuardRail blocked outbound message due to tenant prohibited claim.")
            return GuardRailDecision(
                code="custom_prohibited_claim",
                action="escalate",
                severity="high",
                forced_resolution_status="guardrail_blocked_custom_prohibited_claim",
                message=(
                    "Я не могу автоматически дать такой ответ. Передаю вопрос специалисту, "
                    "чтобы не обещать клиенту неподтвержденные условия."
                ),
            )

        return None

    @classmethod
    def evaluate_tool_call(
        cls,
        tool_name: str,
        payload: Mapping[str, object],
        customer_message: str,
        policy: GuardrailPolicySettings | None = None,
    ) -> GuardRailDecision | None:
        """Block unsafe or unconfirmed tool calls before they reach integrations."""
        if tool_name not in cls.ALLOWED_TOOL_NAMES:
            logger.warning("GuardRail blocked unregistered tool call: %s", tool_name)
            return GuardRailDecision(
                code="unregistered_tool",
                action="block",
                severity="critical",
                forced_resolution_status="guardrail_blocked_unregistered_tool",
                message=(
                    "Я не могу выполнить это действие автоматически. "
                    "Передаю диалог оператору."
                ),
            )

        resolved_policy = policy or GuardrailPolicySettings()
        if not resolved_policy.enabled or not resolved_policy.tool_safety_enabled:
            return None

        if tool_name == "confirm_order" and not cls._has_explicit_confirmation(customer_message):
            logger.warning("GuardRail blocked confirm_order without explicit customer confirmation.")
            return GuardRailDecision(
                code="missing_order_confirmation",
                action="block",
                severity="high",
                forced_resolution_status="guardrail_blocked_unconfirmed_order",
                message=(
                    "Перед оформлением заказа нужно явное подтверждение клиента "
                    "по составу и сумме. Пожалуйста, подтвердите заказ."
                ),
            )

        if tool_name == "add_to_cart":
            quantity = cls._int_payload(payload, "quantity", 1)
            price = cls._int_payload(payload, "price", 0)
            if quantity <= 0 or price < 0:
                logger.warning("GuardRail blocked invalid cart mutation payload.")
                return GuardRailDecision(
                    code="invalid_cart_payload",
                    action="block",
                    severity="high",
                    forced_resolution_status="guardrail_blocked_invalid_cart_payload",
                    message=(
                        "Я не могу выполнить действие с некорректным количеством или ценой. "
                        "Передаю диалог оператору."
                    ),
                )

        if tool_name == "checkout_cart":
            phone = str(payload.get("customer_phone") or "").strip()
            address = str(payload.get("delivery_address") or "").strip()
            if not phone or not address:
                logger.warning("GuardRail blocked checkout without phone or address.")
                return GuardRailDecision(
                    code="missing_checkout_details",
                    action="block",
                    severity="medium",
                    forced_resolution_status="guardrail_blocked_incomplete_checkout",
                    message=(
                        "Для оформления нужны телефон и адрес доставки. "
                        "Пожалуйста, уточните эти данные."
                    ),
                )

        return None

    @classmethod
    def check_inbound_message(cls, message: str) -> str | None:
        decision = cls.evaluate_inbound_message(message)
        return decision.message if decision else None

    @classmethod
    def check_outbound_message(cls, message: str) -> str | None:
        decision = cls.evaluate_outbound_message(message)
        return decision.message if decision else None

    @staticmethod
    def _matches(patterns: list[re.Pattern[str]], message: str) -> bool:
        return any(pattern.search(message) for pattern in patterns)

    @staticmethod
    def _matches_phrases(phrases: list[str], message: str) -> bool:
        normalized_message = " ".join(message.casefold().split())
        return any(phrase.casefold() in normalized_message for phrase in phrases)

    @classmethod
    def _has_explicit_confirmation(cls, customer_message: str) -> bool:
        return cls._matches(cls.EXPLICIT_CONFIRMATION_PATTERNS, customer_message)

    @staticmethod
    def _int_payload(payload: Mapping[str, object], key: str, default: int) -> int:
        value = payload.get(key, default)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return default
