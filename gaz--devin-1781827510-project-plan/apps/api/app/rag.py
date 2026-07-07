import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import openai
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from tenacity import retry, stop_after_attempt, wait_exponential

from app.schemas import KnowledgeChunk, KnowledgeSource, QdrantCollectionContract
from app.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_QDRANT_VECTOR_SIZE = 384
WORD_PATTERN = re.compile(r"\w+")
_MISSING_COLLECTION_LOGGED: set[str] = set()


@dataclass(frozen=True)
class RetrievalResult:
    source_id: UUID
    title: str
    excerpt: str
    score: float


def content_hash(content: str) -> str:
    normalized = " ".join(content.split())
    return sha256(normalized.encode("utf-8")).hexdigest()


def chunk_text(content: str, max_chars: int = 1500, overlap_chars: int = 300) -> list[str]:
    """Split text by paragraphs with max_chars limit and overlap_chars overlap."""
    if not content:
        return []
        
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paragraphs:
        return []
        
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0
    
    for i, p in enumerate(paragraphs):
        p_len = len(p)
        if current_length + p_len > max_chars and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
            # Start new chunk with overlap
            # Find paragraphs to keep from the end of the current_chunk
            actual_overlap_limit = min(overlap_chars, max(0, max_chars - p_len - 2))
            overlap_length = 0
            overlap_paras = []
            for op in reversed(current_chunk):
                if overlap_length + len(op) > overlap_chars:
                    break
                overlap_paras.insert(0, op)
                overlap_length += len(op) + 2
                
            current_chunk = overlap_paras + [p]
            current_length = overlap_length + p_len + 2
            
            # If the current chunk is somehow too large again (e.g. p_len is large),
            # we should make sure we don't exceed max_chars unless it's just a single paragraph
            while current_length > max_chars and len(current_chunk) > 1:
                removed = current_chunk.pop(0)
                current_length -= len(removed) + 2
        else:
            current_chunk.append(p)
            current_length += p_len + 2 # +2 for \n\n
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks


@lru_cache
def _get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    url = settings.effective_qdrant_url
    if url == ":memory:":
        return QdrantClient(location=":memory:")
    return QdrantClient(url=url)


@lru_cache
def _get_local_embedding_model() -> Any:
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("intfloat/multilingual-e5-small")


def _get_openai_client() -> openai.Client:
    settings = get_settings()
    return openai.Client(api_key=settings.openai_api_key)


@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), reraise=True)
def generate_embeddings(
    texts: list[str], dimensions: int = DEFAULT_QDRANT_VECTOR_SIZE
) -> list[list[float]]:
    settings = get_settings()
    if not settings.openai_api_key:
        return [_deterministic_embedding(text, dimensions) for text in texts]

    client = _get_openai_client()
    response = client.embeddings.create(
        input=texts, model="text-embedding-3-small", dimensions=dimensions
    )
    return [d.embedding for d in response.data]


def _deterministic_embedding(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    tokens = WORD_PATTERN.findall(text.casefold())
    if not tokens:
        vector[0] = 1.0
        return vector

    for token in tokens:
        digest = sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = sum(value * value for value in vector) ** 0.5
    if norm == 0:
        vector[0] = 1.0
        return vector
    return [value / norm for value in vector]


def qdrant_point_id(tenant_id: UUID, source_id: UUID, chunk_index: int, chunk_hash: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"gaz-rag:{tenant_id}:{source_id}:{chunk_index}:{chunk_hash}"))


def build_qdrant_collection_contract(
    collection_name: str,
    vector_size: int = DEFAULT_QDRANT_VECTOR_SIZE,
    distance: str = "Cosine",
) -> QdrantCollectionContract:
    return QdrantCollectionContract(
        collection_name=collection_name,
        vector_size=vector_size,
        distance=distance,
        payload_indexes={
            "tenant_id": "keyword",
            "source_id": "keyword",
            "source_type": "keyword",
            "chunk_index": "integer",
            "content_hash": "keyword",
        },
    )


def ensure_collection_exists(client: QdrantClient, contract: QdrantCollectionContract) -> None:
    try:
        client.get_collection(contract.collection_name)
    except (UnexpectedResponse, ValueError) as e:
        if isinstance(e, ValueError) or (
            isinstance(e, UnexpectedResponse) and e.status_code == 404
        ):
            dist = Distance.COSINE if contract.distance == "Cosine" else Distance.EUCLID
            client.create_collection(
                collection_name=contract.collection_name,
                vectors_config=VectorParams(size=contract.vector_size, distance=dist),
            )
        else:
            raise


def _is_missing_collection_error(error: Exception) -> bool:
    if isinstance(error, UnexpectedResponse) and error.status_code == 404:
        return True
    message = str(error).casefold()
    return "collection" in message and "not found" in message


def _log_missing_collection_once(collection_name: str) -> None:
    if collection_name in _MISSING_COLLECTION_LOGGED:
        return
    _MISSING_COLLECTION_LOGGED.add(collection_name)
    logger.info(
        "Qdrant collection %s is not ready; returning empty RAG context.",
        collection_name,
    )


def build_knowledge_chunks(
    source: KnowledgeSource,
    vector_size: int = DEFAULT_QDRANT_VECTOR_SIZE,
) -> list[KnowledgeChunk]:
    chunks = chunk_text(source.content)
    if not chunks:
        return []

    embeddings = generate_embeddings(chunks, vector_size)

    return [
        KnowledgeChunk(
            id=qdrant_point_id(source.tenant_id, source.id, index, content_hash(chunk)),
            tenant_id=source.tenant_id,
            source_id=source.id,
            chunk_index=index,
            content=chunk,
            content_hash=content_hash(chunk),
            embedding=embedding,
            qdrant_payload={
                "tenant_id": str(source.tenant_id),
                "source_id": str(source.id),
                "source_type": source.source_type,
                "title": source.title,
                "chunk_index": str(index),
                "content_hash": content_hash(chunk),
                "content": chunk,  # Include content for retrieval
            },
        )
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False))
    ]


def upsert_chunks_to_qdrant(chunks: list[KnowledgeChunk], collection_name: str) -> None:
    if not chunks:
        return
    client = _get_qdrant_client()
    contract = build_qdrant_collection_contract(collection_name, len(chunks[0].embedding))
    ensure_collection_exists(client, contract)

    points = [
        PointStruct(id=chunk.id, vector=chunk.embedding, payload=chunk.qdrant_payload)
        for chunk in chunks
    ]
    client.upsert(collection_name=collection_name, points=points)


def ingestion_idempotency_key(source: KnowledgeSource) -> str:
    return f"rag-ingestion:{source.tenant_id}:{source.id}:{content_hash(source.content)}"


@lru_cache
def _get_cross_encoder() -> Any:
    from sentence_transformers import CrossEncoder
    # Using a small, fast cross-encoder model
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3), reraise=True)
def retrieve_sources(
    tenant_id: UUID,
    query: str,
    collection_name: str,
    vector_size: int = DEFAULT_QDRANT_VECTOR_SIZE,
    limit: int = 3,
) -> list[RetrievalResult]:
    if not query.strip():
        return []

    query_vector = generate_embeddings([query], vector_size)[0]
    client = _get_qdrant_client()

    from qdrant_client.http.models import FieldCondition, Filter, MatchValue

    try:
        # Fetch more candidates for reranking
        search_result = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=Filter(
                must=[FieldCondition(key="tenant_id", match=MatchValue(value=str(tenant_id)))]
            ),
            limit=limit * 3,
        )
    except Exception as e:
        if _is_missing_collection_error(e):
            _log_missing_collection_once(collection_name)
        else:
            logger.warning("Qdrant search error: %s", e)
        return []

    if not search_result.points:
        return []

    # Prepare pairs for CrossEncoder
    cross_encoder = _get_cross_encoder()
    pairs = []
    for point in search_result.points:
        payload = point.payload or {}
        content = payload.get("content", "")
        pairs.append((query, content))

    # predict returns logits for this model (can be negative)
    # usually > 0 implies relevant, < 0 implies irrelevant
    scores = cross_encoder.predict(pairs)

    ranked_results: list[RetrievalResult] = []
    for point, score in zip(search_result.points, scores, strict=False):
        # Confidence gating: "no answer policy" if score is too low
        # For production with cross-encoder, >0 is usually relevant. We use 0.0 as threshold.
        if score < 0.0:
            continue

        payload = point.payload or {}
        ranked_results.append(
            RetrievalResult(
                source_id=UUID(payload.get("source_id", "00000000-0000-0000-0000-000000000000")),
                title=payload.get("title", "Unknown Source"),
                excerpt=payload.get("content", "")[:300],
                score=float(score),
            )
        )

    # Sort by cross-encoder score descending
    ranked_results.sort(key=lambda x: x.score, reverse=True)
    return ranked_results[:limit]


def compose_grounded_answer(query: str, result: RetrievalResult | None) -> str:
    if not result:
        return (
            "Не нашел надежного источника для ответа. Передаю вопрос оператору "
            "или могу принять контакт для обратного звонка."
        )
    return f"По базе знаний: {result.excerpt}. Источник: {result.title}. Ваш вопрос: {query}"
