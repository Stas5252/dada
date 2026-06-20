from types import SimpleNamespace
from typing import Any

import pytest

from app.llm_router import LLMProvider, LLMRouter, RoutingStrategy


@pytest.mark.asyncio
async def test_local_vllm_can_route_without_openai_key(monkeypatch) -> None:
    router = LLMRouter(
        SimpleNamespace(
            llm_provider="auto",
            openai_api_key="",
            vllm_base_url="http://localhost:8001/v1",
            vllm_api_key="not-needed",
            vllm_model="local-test-model",
        )
    )
    messages = [{"role": "user", "content": "hello"}]

    assert router._select_provider(messages, RoutingStrategy.FASTEST) == LLMProvider.LOCAL_VLLM

    async def fake_local_vllm(
        system_prompt: str,
        routed_messages: list[dict[str, str]],
        **kwargs,
    ) -> tuple[str, list[Any] | None]:
        assert system_prompt == "system"
        assert routed_messages == messages
        return "local answer", None

    monkeypatch.setattr(router, "_call_local_vllm", fake_local_vllm)

    answer, tool_calls = await router.generate_response("system", messages, RoutingStrategy.FASTEST)

    assert answer == "local answer"


def test_provider_preference_falls_back_to_mock_when_required_secret_missing() -> None:
    local_router = LLMRouter(
        SimpleNamespace(llm_provider="local", openai_api_key="", vllm_base_url="")
    )
    openai_router = LLMRouter(
        SimpleNamespace(llm_provider="openai", openai_api_key="", vllm_base_url="")
    )
    messages = [{"role": "user", "content": "hello"}]

    assert local_router._select_provider(messages, RoutingStrategy.FASTEST) == LLMProvider.MOCK
    assert openai_router._select_provider(messages, RoutingStrategy.SMARTEST) == LLMProvider.MOCK
