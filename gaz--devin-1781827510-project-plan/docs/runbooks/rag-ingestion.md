# RAG ingestion runbook

The local MVP ingestion path is Qdrant-ready but does not call Qdrant, LLMs, or
embedding APIs. It chunks source content, creates deterministic local embeddings,
builds Qdrant-compatible point IDs/payloads, and records an ingestion job through
the inline background job backend.

## Local config

Defaults are safe for local development and require no secrets:

```env
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=gaz_knowledge_chunks
QDRANT_VECTOR_SIZE=16
QDRANT_DISTANCE=Cosine
```

`QDRANT_URL` is kept as the future service endpoint, but the current skeleton
only exposes the collection contract and does not make network calls.

## Collection contract

The API exposes the expected Qdrant collection shape:

```bash
curl -H "x-tenant-id: <tenant-id>" \
  http://localhost:8000/api/v1/knowledge/qdrant/contract
```

Expected contract:

- collection: `QDRANT_COLLECTION_NAME`
- vector name: `content`
- vector size: `QDRANT_VECTOR_SIZE`
- distance: `QDRANT_DISTANCE`
- payload indexes: `tenant_id`, `source_id`, `source_type`, `chunk_index`,
  `content_hash`

## Ingest a source

Creating a knowledge source enqueues ingestion automatically through the local
inline backend:

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/sources \
  -H "content-type: application/json" \
  -H "x-tenant-id: <tenant-id>" \
  -d '{
    "title": "Delivery FAQ",
    "source_type": "manual",
    "content": "Delivery takes 45 minutes. Free delivery starts at 1000 rubles."
  }'
```

Re-run ingestion explicitly when needed:

```bash
curl -X POST \
  -H "x-tenant-id: <tenant-id>" \
  http://localhost:8000/api/v1/knowledge/sources/<source-id>/ingest
```

The idempotency key is derived from tenant, source, and content hash, so repeated
runs for unchanged content return the existing job and do not duplicate chunks.

## Inspect jobs

```bash
curl -H "x-tenant-id: <tenant-id>" \
  http://localhost:8000/api/v1/knowledge/ingestion/jobs

curl -H "x-tenant-id: <tenant-id>" \
  http://localhost:8000/api/v1/knowledge/ingestion/jobs/<job-id>
```

Job statuses are `queued`, `running`, `completed`, and `failed`.

## No-answer behavior

`POST /api/v1/chat/mock` retrieves only tenant knowledge with lexical overlap.
When no source matches, the mock answer escalates to a human path with
`resolution_status=needs_human`, low confidence, and no source IDs.

## Future Qdrant integration checklist

Before replacing the local stub with real Qdrant writes:

1. Keep ingestion idempotency keys and deterministic point IDs.
2. Create the collection using the exposed contract before upserting points.
3. Upsert vectors with the existing payload keys for tenant filtering.
4. Keep tests runnable with the local stub and gate real Qdrant tests behind an
   explicit opt-in environment flag.
