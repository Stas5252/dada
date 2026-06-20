CREATE TABLE auth_sessions (
  id VARCHAR(36) PRIMARY KEY,
  tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id),
  user_id VARCHAR(36) NOT NULL REFERENCES users(id),
  refresh_token_hash VARCHAR(64) NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  replaced_by_session_id VARCHAR(36),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_session_refresh_token_hash UNIQUE (refresh_token_hash)
);

CREATE INDEX idx_auth_sessions_tenant_id ON auth_sessions(tenant_id);
CREATE INDEX idx_auth_sessions_user_id ON auth_sessions(user_id);
CREATE INDEX idx_auth_sessions_expires_at ON auth_sessions(expires_at);
