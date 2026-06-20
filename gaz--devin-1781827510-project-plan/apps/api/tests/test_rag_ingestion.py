from uuid import uuid4

from app.schemas import (
    AgentCreateRequest,
    ChatMessageRequest,
    KnowledgeIngestionJobStatus,
    KnowledgeSourceCreateRequest,
    KnowledgeSourceStatus,
)
from app.store import InMemoryStore


def test_create_source_runs_idempotent_local_ingestion() -> None:
    store = InMemoryStore()
    tenant_id = uuid4()
    source = store.create_knowledge_source(
        tenant_id,
        KnowledgeSourceCreateRequest(
            title="Delivery FAQ",
            source_type="manual",
            content="Delivery takes 45 minutes. " * 80,
        ),
    )

    first_job = store.enqueue_knowledge_ingestion(tenant_id, source.id)
    second_job = store.enqueue_knowledge_ingestion(tenant_id, source.id)

    assert first_job is not None
    assert second_job is not None
    assert first_job.id == second_job.id
    assert first_job.status == KnowledgeIngestionJobStatus.completed
    assert source.status == KnowledgeSourceStatus.indexed
    assert source.chunk_count > 1
    assert len(store.knowledge_chunks) == source.chunk_count


def test_mock_chat_no_answer_policy_escalates_without_sources(monkeypatch) -> None:
    store = InMemoryStore()
    tenant_id = uuid4()

    monkeypatch.setattr("app.store.retrieve_sources", lambda *args, **kwargs: [])

    agent = store.create_agent(
        tenant_id,
        AgentCreateRequest(
            name="Support bot",
            prompt="Answer only from knowledge. Escalate unknowns.",
        ),
    )
    store.create_knowledge_source(
        tenant_id,
        KnowledgeSourceCreateRequest(
            title="Billing FAQ",
            source_type="manual",
            content="Cards and cash are supported at checkout.",
        ),
    )

    answer = store.answer_chat(
        tenant_id,
        ChatMessageRequest(
            agent_id=agent.id,
            message="Do you repair bicycles?",
        ),
    )

    assert answer is not None
    conversation, _customer_message, agent_message, sources = answer
    assert conversation.resolution_status == "needs_human"
    assert agent_message.source_ids == []
    assert sources == []
    assert "Передаю вопрос оператору" in agent_message.content
