CREATE TABLE knowledge_ingestion_jobs (
  id VARCHAR(36) PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
  source_id VARCHAR(36) NOT NULL REFERENCES knowledge_sources(id),
  status VARCHAR(40) NOT NULL,
  idempotency_key VARCHAR(160) NOT NULL,
  qdrant_collection VARCHAR(120) NOT NULL,
  background_backend VARCHAR(80) NOT NULL,
  chunk_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_knowledge_ingestion_idempotency_key UNIQUE (idempotency_key)
);

CREATE TABLE knowledge_chunks (
  id VARCHAR(36) PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
  source_id VARCHAR(36) NOT NULL REFERENCES knowledge_sources(id),
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  content_hash VARCHAR(64) NOT NULL,
  embedding JSONB NOT NULL,
  qdrant_payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_knowledge_chunk_source_index UNIQUE (source_id, chunk_index)
);

CREATE INDEX idx_knowledge_ingestion_jobs_tenant_id ON knowledge_ingestion_jobs(tenant_id);
CREATE INDEX idx_knowledge_ingestion_jobs_source_id ON knowledge_ingestion_jobs(source_id);
CREATE INDEX idx_knowledge_chunks_tenant_id ON knowledge_chunks(tenant_id);
CREATE INDEX idx_knowledge_chunks_source_id ON knowledge_chunks(source_id);
