from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.orchestrator import AgentOrchestrator
from app.schemas import AgentCreateRequest
from app.store_factory import get_app_store

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"

@pytest.mark.anyio
async def test_memory_summarization_triggers_on_long_conversations(monkeypatch):
    store = get_app_store()
    
    # 1. Create an agent
    agent = store.create_agent(
        UUID(DEMO_TENANT_ID),
        AgentCreateRequest(name="Memory Agent", prompt="Помогай клиентам вежливо.")
    )

    # 2. Create conversation ID
    conversation_id = uuid4()
    
    # Add 12 turns (24 messages) to exceed threshold (> 10)
    for i in range(12):
        store.record_chat_turn(
            tenant_id=UUID(DEMO_TENANT_ID),
            agent_id=agent.id,
            conversation_id=conversation_id,
            channel="web_widget",
            customer_text=f"Сообщение клиента {i}",
            agent_response_text=f"Ответ ассистента {i}"
        )

    # Mock the LLM router to return a summary
    mock_generate = AsyncMock(return_value=("Резюме: клиент спросил про пиццу.", []))
    
    # Instantiate orchestrator
    from app.settings import get_settings
    orchestrator = AgentOrchestrator(store, get_settings())
    
    # Mock router generate_response method
    monkeypatch.setattr(orchestrator.router, "generate_response", mock_generate)

    # Process next message
    await orchestrator.process_message(
        tenant_id=UUID(DEMO_TENANT_ID),
        agent_id=agent.id,
        conversation_id=conversation_id,
        customer_message="Еще один вопрос",
        channel="web_widget"
    )

    # Verify that the LLM router was called to generate the summary
    assert mock_generate.called
    
    # Verify that the summary was saved to store
    conv = store.get_conversation(UUID(DEMO_TENANT_ID), conversation_id)
    assert conv is not None
    assert conv.summary == "Резюме: клиент спросил про пиццу."
