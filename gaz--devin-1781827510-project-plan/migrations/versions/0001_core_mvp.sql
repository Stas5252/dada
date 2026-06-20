CREATE TABLE tenants (
  id VARCHAR(36) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  plan VARCHAR(40) NOT NULL DEFAULT 'start',
  status VARCHAR(40) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id VARCHAR(36) PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
  email VARCHAR(320) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(120) NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE memberships (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
  user_id VARCHAR(36) NOT NULL REFERENCES users(id),
  role VARCHAR(40) NOT NULL,
  CONSTRAINT uq_membership_tenant_user UNIQUE (tenant_id, user_id)
);

CREATE TABLE agents (
  id VARCHAR(36) PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
  name VARCHAR(120) NOT NULL,
  prompt TEXT NOT NULL,
  channel VARCHAR(40) NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'draft',
  version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE knowledge_sources (
  id VARCHAR(36) PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
  title VARCHAR(160) NOT NULL,
  source_type VARCHAR(40) NOT NULL,
  content TEXT NOT NULL,
  status VARCHAR(40) NOT NULL,
  chunk_count INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE conversations (
  id VARCHAR(36) PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
  agent_id VARCHAR(36) NOT NULL REFERENCES agents(id),
  channel VARCHAR(40) NOT NULL,
  status VARCHAR(40) NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  resolution_status VARCHAR(40) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
  id VARCHAR(36) PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
  conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id),
  role VARCHAR(40) NOT NULL,
  content TEXT NOT NULL,
  confidence DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_memberships_tenant_id ON memberships(tenant_id);
CREATE INDEX idx_agents_tenant_id ON agents(tenant_id);
CREATE INDEX idx_knowledge_sources_tenant_id ON knowledge_sources(tenant_id);
CREATE INDEX idx_conversations_tenant_created ON conversations(tenant_id, created_at);
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);
