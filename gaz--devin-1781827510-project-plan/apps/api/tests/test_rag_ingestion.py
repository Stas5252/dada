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
    from app.store_factory import get_app_store
    store = get_app_store()
    tenant_id = uuid4()
    source = store.create_knowledge_source(
        tenant_id,
        KnowledgeSourceCreateRequest(
            title="Delivery FAQ",
            source_type="manual",
            content="Delivery takes 45 minutes.\n\n" * 80,
        ),
    )

    first_job = store.enqueue_knowledge_ingestion(tenant_id, source.id)
    second_job = store.enqueue_knowledge_ingestion(tenant_id, source.id)

    assert first_job is not None
    assert second_job is not None
    first_job = store.get_ingestion_job(tenant_id, first_job.id)
    source = store.get_knowledge_source(tenant_id, source.id)
    assert first_job.status == KnowledgeIngestionJobStatus.completed
    assert source.status == KnowledgeSourceStatus.indexed
    assert source.chunk_count > 1


def test_mock_chat_no_answer_policy_escalates_without_sources(monkeypatch) -> None:
    from app.store_factory import get_app_store
    from app.schemas import RegisterRequest
    store = get_app_store()
    
    reg_payload = RegisterRequest(
        company_name="RAG Tenant",
        owner_email=f"rag_{uuid4().hex}@example.com",
        owner_name="RAG Owner",
        password="safe-password-123",
    )
    from app.settings import get_settings
    settings = get_settings()
    tenant, user, token = store.register(reg_payload, settings.access_token_secret)
    tenant_id = tenant.id

    from app.llm_router import LLMRouter
    class MockToolCall:
        class function:
            name = "escalate_to_human"
            arguments = "{}"
            
    async def mock_generate_response(*args, **kwargs):
        print("MOCK GENERATE RESPONSE CALLED!")
        return "", [MockToolCall()]

    monkeypatch.setattr(LLMRouter, "generate_response", mock_generate_response)

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
            content="Cards and cash are supported at checkout."        ),
    )

    from fastapi.testclient import TestClient
    from app.main import create_app
    app = create_app()
    client = TestClient(app)
    
    headers = {
        "x-tenant-id": str(tenant_id),
        "Authorization": f"Bearer {token}"
    }
    
    chat_response = client.post(
        "/api/v1/chat/mock",
        headers=headers,
        json={
            "agent_id": str(agent.id),
            "channel": "web_widget",
            "message": "Do you repair bicycles?",
        },
    )
    
    assert chat_response.status_code == 201
    chat_payload = chat_response.json()
    print("CHAT PAYLOAD:", chat_payload)
    assert chat_payload["conversation"]["resolution_status"] == "needs_human"
    assert chat_payload["agent_message"]["source_ids"] == []
    assert "Перевожу вас на старшего специалиста" in chat_payload["agent_message"]["content"]
