from uuid import uuid4

from app.rag import (
    build_knowledge_chunks,
    build_qdrant_collection_contract,
    chunk_text,
    compose_grounded_answer,
    retrieve_sources,
)
from app.schemas import KnowledgeSource


def test_chunk_text_normalizes_whitespace() -> None:
    assert chunk_text("hello\n\nworld", max_chars=5) == ["hello", "world"]


def test_build_knowledge_chunks_has_stable_qdrant_points() -> None:
    source = KnowledgeSource(
        id=uuid4(),
        tenant_id=uuid4(),
        title="FAQ",
        source_type="manual",
        content="First answer. " * 150,
    )

    first_chunks = build_knowledge_chunks(source)
    second_chunks = build_knowledge_chunks(source)

    assert len(first_chunks) >= 1
    assert len(second_chunks) >= 1
    assert [chunk.id for chunk in first_chunks] == [chunk.id for chunk in second_chunks]
    assert {len(chunk.embedding) for chunk in first_chunks} == {384}
    assert first_chunks[0].qdrant_payload["tenant_id"] == str(source.tenant_id)


def test_qdrant_contract_is_local_only() -> None:
    contract = build_qdrant_collection_contract("gaz_knowledge_chunks", vector_size=16)

    assert contract.collection_name == "gaz_knowledge_chunks"
    assert contract.vector_size == 16
    assert contract.distance == "Cosine"
    assert contract.payload_indexes["tenant_id"] == "keyword"


def test_retrieve_sources_ranks_matching_source() -> None:
    delivery = KnowledgeSource(
        id=uuid4(),
        tenant_id=uuid4(),
        title="Delivery",
        source_type="manual",
        content="Delivery takes 45 minutes in Moscow.",
    )
    billing = KnowledgeSource(
        id=uuid4(),
        tenant_id=delivery.tenant_id,
        title="Billing",
        source_type="manual",
        content="Cards and cash are supported.",
    )

    collection_name = f"test_collection_{uuid4().hex}"
    from app.rag import build_knowledge_chunks, upsert_chunks_to_qdrant

    chunks = build_knowledge_chunks(delivery) + build_knowledge_chunks(billing)
    upsert_chunks_to_qdrant(chunks, collection_name)

    results = retrieve_sources(delivery.tenant_id, "delivery minutes", collection_name)

    assert "Delivery" in [result.title for result in results]


def test_compose_grounded_answer_has_no_answer_policy() -> None:
    assert "Передаю вопрос оператору" in compose_grounded_answer("unknown", None)
