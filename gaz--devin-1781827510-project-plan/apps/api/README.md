# gaz-api

FastAPI backend skeleton for the AI support platform.

## Core MVP chat slice

The current backend exposes placeholder Core MVP endpoints under `/api/v1`:

- `POST /auth/register` and `POST /auth/login` issue JWT access tokens and
  opaque refresh tokens backed by revocable auth sessions.
- `POST /auth/refresh` rotates refresh tokens and `POST /auth/logout` revokes
  the presented refresh session.
- `GET /auth/me`, `POST /auth/login/mfa`, `POST /auth/mfa/setup`,
  `POST /auth/mfa/verify`, `POST /auth/mfa/recovery-codes`, and
  `POST /auth/mfa/disable` expose account security without returning TOTP
  secrets or recovery-code hashes in public user responses.
- `POST /auth/verify-email`, `POST /auth/request-password-reset`, and
  `POST /auth/reset-password` cover the basic account recovery flow.
- `GET /tenants/{tenant_id}/dashboard` returns tenant-scoped counts for agents,
  knowledge sources and conversations.
- `POST /agents`, `GET /agents`, `GET /agents/{agent_id}`,
  `PATCH /agents/{agent_id}`, and `POST /agents/{agent_id}/publish` manage
  draft/published support agents. Editing prompt or channel increments the
  version and returns the agent to draft until it is republished.
- `POST /knowledge/sources`, `GET /knowledge/sources`, `POST /knowledge/upload`,
  and `POST /knowledge/sources/{source_id}/ingest` manage sources, UTF-8
  `.txt/.md/.csv` uploads and local idempotent ingestion jobs.
- `GET /knowledge/ingestion/jobs` and `/knowledge/qdrant/contract` expose the
  background job state and Qdrant-ready collection contract without network calls.
- `GET /conversations` and `GET /conversations/{conversation_id}` expose chat logs.
- `POST /chat/mock` creates a conversation turn and returns a grounded mock answer with citations.

Business endpoints accept bearer access tokens for tenant isolation. Local development
can still use the legacy `x-tenant-id` fallback when `ALLOW_LEGACY_TENANT_HEADER=true`;
staging and production should disable that fallback. The repository layer supports both
in-memory and SQLAlchemy-backed persistence without changing endpoint contracts.

## Local commands

```bash
uv sync --extra dev
uv run uvicorn app.main:create_app --factory --reload
uv run pytest
uv run ruff check app tests
uv run mypy app
```
