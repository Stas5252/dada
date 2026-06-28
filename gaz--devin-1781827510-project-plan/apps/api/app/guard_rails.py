import logging
import re

logger = logging.getLogger(__name__)

class GuardRailError(Exception):
    pass

class RuntimeGuardRails:
    # Basic patterns for MVP. In a production system, these might use an LLM-based classifier.
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
        re.compile(r"system\s+override", re.IGNORECASE),
        re.compile(r"you\s+are\s+now", re.IGNORECASE),
        re.compile(r"забудь\s+все", re.IGNORECASE),
        re.compile(r"забудь\s+предыдущие", re.IGNORECASE),
        re.compile(r"теперь\s+ты", re.IGNORECASE),
    ]

    # Simple dictionary check for basic profanity / unacceptable tone
    UNACCEPTABLE_PATTERNS = [
        re.compile(r"\b(хуй|пизд|еба|бля|сука|мудак|хер)\b", re.IGNORECASE),
    ]

    @classmethod
    def check_inbound_message(cls, message: str) -> str | None:
        """
        Check customer message for prompt injection or severe toxicity.
        Returns a safe fallback message if blocked, or None if passed.
        """
        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(message):
                logger.warning("GuardRail blocked inbound message due to injection pattern.")
                return "Извините, я не могу обрабатывать такие команды. Чем я могу помочь по существу?"
        for pattern in cls.UNACCEPTABLE_PATTERNS:
            if pattern.search(message):
                logger.warning("GuardRail detected severe toxicity in inbound message.")
                return "Пожалуйста, давайте общаться уважительно. Если у вас срочный вопрос — могу перевести на оператора."
        return None

    @classmethod
    def check_outbound_message(cls, message: str) -> str | None:
        """
        Check agent response for swearing, inappropriate tone, or safety limits.
        Returns a fallback safe message if blocked, or None if passed.
        """
        for pattern in cls.UNACCEPTABLE_PATTERNS:
            if pattern.search(message):
                logger.warning("GuardRail blocked outbound message due to unacceptable content.")
                return "Извините, произошла ошибка генерации ответа. Пожалуйста, перефразируйте вопрос или попросите перевести на оператора."
        return None
