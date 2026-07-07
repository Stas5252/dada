# Testing

## Local quality gates

Backend:

```bash
cd apps/api
python -m ruff check app tests
python -m mypy app --show-error-codes
python -m pytest
python -m bandit -q -r app
python -m safety check --full-report
python -m alembic heads
```

Frontend:

```bash
cd apps/web
npm run lint
npm run typecheck
npm run build
npx playwright test --reporter=list
```

For repeated local Playwright runs, start the API as `APP_ENV=local` with
`RATE_LIMIT_ENABLED=false`; do not use `APP_ENV=test` for browser e2e because it
runs background jobs inline and can make Testbed run requests block.

```powershell
cd apps/api
$env:APP_ENV="local"
$env:RATE_LIMIT_ENABLED="false"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Workspace:

```bash
npm test
npm audit --audit-level=moderate
git diff --check
```

## Current verified result

As of 2026-07-07:

- Backend tests: 138/138 passed.
- Playwright tests: 11/11 passed.
- Backend lint/type/security scans passed.
- Frontend lint/type/build/audit passed.
- Runtime guardrail/channel-policy/billing/webhook/Testbed/RAG-eval tests cover opt-out escalation, unsafe order tool-call blocking, durable contact suppression/outbound-call blocking, durable contact consent create/list/revoke/expiry behavior, consent-required operator outbound blocking and voice outbound blocking, per-tenant guardrail policy API round-trip, settings merge behavior, custom regulated phrases, custom prohibited outbound claims, hard tool allowlist enforcement, channel policy API round-trip, integration readiness API checks, channel webhook diagnostics without secret leakage, WhatsApp app-secret setup gaps, Testbed readiness pass-rate/latest-run summaries, publish-block pass-rate details, tenant-scoped RAG eval citations/expected terms/no-answer checks, billing status remaining/limit reporting, billing-limit `402` blocking with audit log, web-widget draft-only behavior, web-widget auto-reply caps, VK human-approval blocking of external auto-send and Telegram opt-out notice injection.
- RAG fallback tests cover missing Qdrant collection behavior: it returns empty context without ERROR logs. RAG eval tests cover local golden-case quality gates without requiring live Qdrant/OpenAI, and browser e2e covers the RAG eval panel on the knowledge page.
- Docker checks were not run because Docker is not installed on the workstation.

## Manual QA checklist

Before release, manually verify:

- Register a new tenant.
- Log in and refresh/logout.
- Create an agent.
- Edit/publish agent.
- Upload or add knowledge.
- Run Testbed scenario.
- Use web widget.
- Send message in at least one real channel.
- Trigger operator handoff.
- Create billing checkout in sandbox.
- Verify audit logs.
- Verify readiness and monitoring.

## Missing test coverage

- Real Docker compose startup on clean machine.
- Real SIP/Twilio/Asterisk call.
- Streaming STT/TTS latency and barge-in.
- YooKassa sandbox webhook lifecycle.
- Real Telegram/VK/WhatsApp webhook smoke.
- Load tests for chat and voice concurrency.
- Larger RAG golden datasets and CI threshold enforcement.
- Backup/restore integration drill.
