import logging
from enum import Enum
from typing import Any

import openai

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    LOCAL_VLLM = "local_vllm"
    OPENAI = "openai"
    MOCK = "mock"


class RoutingStrategy(Enum):
    FASTEST = "fastest"
    SMARTEST = "smartest"
    BALANCED = "balanced"


DEFAULT_OPENAI_FAST_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_SMART_MODEL = "gpt-4o"
DEFAULT_VLLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TIMEOUT_SECONDS = 30.0


class LLMRouter:
    def __init__(self, settings: Any):
        self.settings = settings
        self._openai_client: openai.AsyncClient | None = None
        api_key = self._setting("openai_api_key")
        if api_key:
            self._openai_client = openai.AsyncClient(
                api_key=api_key,
                timeout=self._timeout_seconds,
            )

    async def generate_response(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
        tenant_settings: dict[str, Any] | None = None,
    ) -> tuple[str, list[Any] | None]:
        provider = self._select_provider(messages, strategy, tenant_settings=tenant_settings)
        logger.info("Routing LLM request to provider: %s", provider.value)

        if provider == LLMProvider.LOCAL_VLLM:
            return await self._call_local_vllm(system_prompt, messages, tools=tools, max_tokens=max_tokens)
        if provider == LLMProvider.OPENAI:
            return await self._call_openai(system_prompt, messages, strategy, tools=tools, max_tokens=max_tokens, tenant_settings=tenant_settings)
        return self._mock_generation(messages), None

    def _select_provider(
        self,
        messages: list[dict[str, str]],
        strategy: RoutingStrategy,
        tenant_settings: dict[str, Any] | None = None,
    ) -> LLMProvider:
        provider_preference = self._setting("llm_provider", "auto").lower()
        has_local = bool(self._setting("vllm_base_url"))
        
        tenant_openai_key = tenant_settings.get("openai_api_key") if tenant_settings else None
        has_openai = bool(tenant_openai_key) or self._openai_client is not None

        if provider_preference in {"mock", "test"}:
            return LLMProvider.MOCK
        if provider_preference in {"local", "local_vllm", "vllm"}:
            return LLMProvider.LOCAL_VLLM if has_local else LLMProvider.MOCK
        if provider_preference == "openai":
            return LLMProvider.OPENAI if has_openai else LLMProvider.MOCK

        if strategy == RoutingStrategy.FASTEST:
            if has_local:
                return LLMProvider.LOCAL_VLLM
            return LLMProvider.OPENAI if has_openai else LLMProvider.MOCK

        if strategy == RoutingStrategy.SMARTEST:
            if has_openai:
                return LLMProvider.OPENAI
            return LLMProvider.LOCAL_VLLM if has_local else LLMProvider.MOCK

        total_length = sum(len(message.get("content", "")) for message in messages)
        if total_length > 2000 and has_openai:
            return LLMProvider.OPENAI
        if has_local:
            return LLMProvider.LOCAL_VLLM
        return LLMProvider.OPENAI if has_openai else LLMProvider.MOCK

    async def _call_openai(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
        tenant_settings: dict[str, Any] | None = None,
    ) -> tuple[str, list[Any] | None]:
        tenant_openai_key = tenant_settings.get("openai_api_key") if tenant_settings else None
        
        client = None
        if tenant_openai_key:
            client = openai.AsyncClient(api_key=tenant_openai_key, timeout=self._timeout_seconds)
        else:
            client = self._openai_client

        if not client:
            return self._mock_generation(messages), None

        model = (
            self._setting("openai_smart_model", DEFAULT_OPENAI_SMART_MODEL)
            if strategy == RoutingStrategy.SMARTEST
            else self._setting("openai_fast_model", DEFAULT_OPENAI_FAST_MODEL)
        )
        return await self._call_openai_compatible(
            client=client,
            model=model,
            system_prompt=system_prompt,
            messages=messages,
            fallback_label=f"OpenAI {model}",
            tools=tools,
            max_tokens=max_tokens,
        )

    async def _call_local_vllm(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> tuple[str, list[Any] | None]:
        base_url = self._setting("vllm_base_url")
        if not base_url:
            return self._mock_generation(messages), None

        client = openai.AsyncClient(
            api_key=self._setting("vllm_api_key", "not-needed"),
            base_url=base_url,
            timeout=self._timeout_seconds,
        )
        return await self._call_openai_compatible(
            client=client,
            model=self._setting("vllm_model", DEFAULT_VLLM_MODEL),
            system_prompt=system_prompt,
            messages=messages,
            fallback_label="local vLLM",
            tools=tools,
            max_tokens=max_tokens,
        )

    async def _call_openai_compatible(
        self,
        *,
        client: openai.AsyncClient,
        model: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        fallback_label: str,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> tuple[str, list[Any] | None]:
        try:
            api_messages = self._api_messages(system_prompt, messages)
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens or self._max_tokens,
                "temperature": self._temperature,
            }
            if tools:
                kwargs["tools"] = tools

            response = await client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            content = message.content or ""

            tool_calls = message.tool_calls

            if content or tool_calls:
                logger.info(
                    "%s response: %s chars, %s tool calls",
                    fallback_label,
                    len(content),
                    len(tool_calls) if tool_calls else 0,
                )
                return content.strip(), tool_calls
            logger.warning("%s returned an empty response", fallback_label)
        except openai.RateLimitError:
            logger.warning("%s rate limit hit, falling back to mock", fallback_label)
        except openai.APIConnectionError as exc:
            logger.error("%s connection error: %s", fallback_label, exc)
        except openai.APIError as exc:
            logger.error("%s API error: %s", fallback_label, exc)
        except Exception as exc:
            logger.error("Unexpected %s error: %s", fallback_label, exc)
        return self._mock_generation(messages), None

    @staticmethod
    def _api_messages(
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        api_messages = [{"role": "system", "content": system_prompt}]
        is_first = True
        for message in messages:
            if is_first and message.get("role") == "system" and message.get("content") == system_prompt:
                is_first = False
                continue
            api_messages.append(message)
        return api_messages

    def _mock_generation(self, messages: list[dict[str, str]]) -> str:
        last_msg = (messages[-1]["content"] if messages else "").lower()
        system_msg = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""

        # Conversational Pizza Shop Agent simulation
        if "KNOWLEDGE BASE CONTENT:" in system_msg and "Delivery FAQ" in system_msg:
            return (
                "Я проверил базу знаний (Delivery FAQ). По правилам доставки: "
                f"мы доставляем за 45-60 минут. Вы спросили: '{messages[-1]['content']}'"
            )
        elif any(
            w in last_msg for w in ["привет", "здравствуйте", "добрый", "начать", "hello", "hi"]
        ):
            return (
                "Здравствуйте! Вас приветствует пиццерия Demo Pizza. "
                "Какую пиццу желаете заказать?"
            )
        elif any(w in last_msg for w in ["меню", "пицц", "выбор", "какие", "что есть"]):
            return (
                "В нашем меню: Пепперони (30 см) — 599₽, Маргарита (30 см) — 499₽, "
                "Четыре сыра (30 см) — 649₽. Что вам предложить?"
            )
        elif any(w in last_msg for w in ["пепперони", "маргарит", "сыр", "pepperoni", "margarita"]):
            return "Отличный выбор! Назовите, пожалуйста, адрес и улицу для доставки."
        elif any(w in last_msg for w in ["ул", "улиц", "дом", "кв", "адрес", "невски"]):
            return (
                "Адрес доставки записан. Пожалуйста, подтвердите заказ: Пицца 30 см, "
                "доставка по указанному адресу. Всё верно?"
            )
        elif any(w in last_msg for w in ["да", "верно", "подтвержда", "ок", "хорошо"]):
            return (
                "Заказ успешно оформлен и передан на кухню! Доставка займет 45-60 минут. "
                "Спасибо за заказ!"
            )
        elif any(w in last_msg for w in ["время", "сколько", "доставк", "цена", "стоимость"]):
            return (
                "Доставка обычно занимает 45–60 минут. При заказе от 1000₽ "
                "доставка бесплатная, иначе — 150₽."
            )

        return (
            "Я вас понял. Могу предложить оформить заказ на Пепперони, Маргариту "
            f"или рассказать о времени доставки. Вы сказали: '{messages[-1]['content']}'"
        )

    def _setting(self, name: str, default: str = "") -> str:
        return str(getattr(self.settings, name, default) or default)

    @property
    def _max_tokens(self) -> int:
        return int(getattr(self.settings, "llm_max_tokens", DEFAULT_MAX_TOKENS))

    @property
    def _temperature(self) -> float:
        return float(getattr(self.settings, "llm_temperature", DEFAULT_TEMPERATURE))

    @property
    def _timeout_seconds(self) -> float:
        return float(getattr(self.settings, "llm_timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
