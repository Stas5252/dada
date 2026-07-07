# Local development runbook

## Install dependencies

```bash
make install
```

## Start infrastructure

```bash
make infra-up
```

Validate the compose file without starting services:

```bash
make compose-config
```

The compose stack uses local-only defaults from `.env.example`; do not add real
secrets to `.env.example` or commit `.env`.

## Start API

```bash
make api-dev
```

Healthcheck:

```bash
curl http://localhost:8000/api/v1/health
```

Local API seeds the demo tenant when `SEED_DEMO_DATA=true`:

```bash
make seed-demo
curl -H "x-tenant-id: 00000000-0000-0000-0000-000000000001" \
  http://localhost:8000/api/v1/tenants/00000000-0000-0000-0000-000000000001/dashboard
```

## Start frontend

```bash
make web-dev
```

Open `http://localhost:3000` in the browser.

Live MVP smoke paths:

- `http://localhost:3000/agents/new` creates a draft agent through the Core API.
- `http://localhost:3000/knowledge` creates a text knowledge source through the Core API.
- `http://localhost:3000/test-console` sends a mock chat message and links to the created conversation.

For live dashboard data, keep these frontend variables aligned with the API:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_TENANT_ID=00000000-0000-0000-0000-000000000001
NEXT_PUBLIC_WIDGET_AGENT_ID=389a4f13-05d3-5860-af9f-69bd9ce2493a
```

Business API routes accept bearer tokens and verify tenant mismatch when an
`x-tenant-id` header is also provided. Local development keeps the legacy
header-only path enabled with `ALLOW_LEGACY_TENANT_HEADER=true`; set it to
`false` in staging/production.

For browser widget smoke checks, ensure the API allows the web origin:

```bash
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Local `APP_ENV=local` uses in-memory rate-limit storage by default, so the API
does not require Redis just to run public endpoints. In staging/production, set
`RATE_LIMIT_STORAGE_URI` or a reachable `REDIS_URL`.

For repeated local Playwright runs, keep `APP_ENV=local` and start the API with
`RATE_LIMIT_ENABLED=false`. This avoids registration throttling during parallel
e2e tests while preserving async background jobs for Testbed runs.

Web widget smoke endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/widget/chat/389a4f13-05d3-5860-af9f-69bd9ce2493a \
  -H "content-type: application/json" \
  -d '{"session_id":"local_widget_session_123","message":"Сколько стоит доставка?"}'
```

Voice preview smoke endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/voice/sessions/local-voice-preview-1/preview-turn \
  -H "authorization: Bearer <access token>" \
  -H "x-tenant-id: <tenant id>" \
  -H "content-type: application/json" \
  -d '{"agent_id":"<agent id>","text":"Здравствуйте, хочу уточнить время доставки."}'
```

The response includes `conversation_id`. Open
`http://localhost:3000/conversations/<conversation_id>` or use `/test-console`
Voice preview to inspect the saved transcript.

## Local AI / vLLM

The backend LLM router reads `VLLM_BASE_URL` directly. When it is configured,
`LLM_PROVIDER=auto` uses the local OpenAI-compatible endpoint for fast routes
even if `OPENAI_API_KEY` is empty.

```bash
LLM_PROVIDER=auto
VLLM_BASE_URL=http://localhost:8001/v1
VLLM_API_KEY=not-needed
VLLM_MODEL=Qwen/Qwen2.5-7B-Instruct
OPENAI_API_KEY=
```

Validate readiness:

```bash
curl http://localhost:8000/api/v1/readiness
```

The `llm` provider should be `configured` when `VLLM_BASE_URL` or
`OPENAI_API_KEY` is set. With neither set, local development falls back to the
deterministic mock LLM response.

Auth session smoke flow:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "content-type: application/json" \
  -d '{"email":"owner@demo-pizza.example.com","password":"safe-local-password"}'

curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "content-type: application/json" \
  -d '{"refresh_token":"<refresh token from login>"}'

curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "content-type: application/json" \
  -d '{"refresh_token":"<latest refresh token>"}'
```

Refresh tokens are rotated and previous refresh tokens are rejected after use.

## Quality gates

```bash
make lint
make typecheck
make test
make build
make audit
make pre-commit
```

## Operational drills

These skeleton drills run without real secrets:

```bash
make backup-restore-drill DRILL_ARGS=--dry-run
make migration-dry-run DRILL_ARGS=--dry-run
make smoke-check DRILL_ARGS=--dry-run
```

Full runbooks:

- [Backup restore drill](backup-restore-drill.md)
- [Migration dry-run](migration-dry-run.md)
- [RAG ingestion](rag-ingestion.md)
- [Smoke checks](smoke-checks.md)

## Stop local infrastructure

```bash
make infra-down
```
