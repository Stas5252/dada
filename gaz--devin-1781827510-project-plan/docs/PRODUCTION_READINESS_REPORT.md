# Production readiness report (2026-07-07)

## Status

Current status: strong local/staging candidate, not yet proven enterprise production.

The application starts locally, core automated checks pass, and the architecture has the right modules for an enterprise SaaS. The missing proof is real infrastructure and real external-provider verification.

## Commands run and results

Backend:

| Command | Result |
| --- | --- |
| `python -m ruff check app tests` | Passed |
| `python -m mypy app --show-error-codes` | Passed, 81 source files |
| `python -m pytest` | Passed, 138/138 |
| `python -m bandit -q -r app` | Passed |
| `python -m safety check --full-report` | Passed, 0 vulnerabilities |
| `python -m alembic heads` | Passed, one head `6b7c8d9e0f12` |

Frontend/workspace:

| Command | Result |
| --- | --- |
| `npm run lint` | Passed |
| `npm run typecheck` | Passed |
| `npm run build` | Passed |
| `npm test` | Passed |
| `npm audit --audit-level=moderate` | Passed, 0 vulnerabilities |

Browser/runtime:

| Check | Result |
| --- | --- |
| API `/api/v1/health` | HTTP 200 |
| Web `/` on port 3000 | HTTP 200 |
| `npx playwright test --reporter=list` | Passed, 11/11 |

Not run:

- `docker compose config` and full compose startup, because Docker CLI is not installed on this workstation.
- Real payment, telephony and messaging provider checks, because credentials/tokens are not configured.

## Fully working locally

- FastAPI API process.
- Next.js web process.
- Auth/register/login/refresh/logout/MFA foundations.
- Agent CRUD and publish API with Testbed gate for missing, failed, running and stale scenario runs, plus pass-rate readiness summaries.
- Knowledge source APIs, parser coverage and tenant-scoped RAG eval API/UI checks for citations, expected terms and no-answer behavior.
- Conversations and widget/test console flows.
- Runtime guardrail enforcement for opt-out, human handoff intent, regulated topics, unsafe outbound claims and unsafe tool calls.
- Per-tenant guardrail policy API/UI for prompt injection blocking, handoff, regulated topics, toxicity, outbound safety, tool safety, AI disclosure and custom escalation/prohibited-claim phrases.
- Per-channel compliance policy API/UI for `autopilot`, `draft_only`, `human_approval`, AI disclosure, outbound disable controls, opt-out notices, per-conversation auto-reply caps and consent-required outbound controls.
- Per-tenant integration readiness API/UI checklist for LLM, speech, web widget, messaging, voice, payments and order integrations; it reports only setting names, never secret values.
- Per-tenant channel webhook diagnostics API/UI for Telegram, VK and WhatsApp callback URLs, HTTPS status, missing settings and security warnings; secret values are not returned.
- Durable contact suppression/do-not-call storage with API create/list/revoke and outbound-call/operator-send blocking.
- Durable contact consent storage with API create/list/revoke, expiry support and consent-required operator-send/outbound-call blocking.
- Testbed CRUD/readiness smoke, latest-run summaries and agent-page publish readiness panel.
- Billing ledger/provider foundations, monthly message-limit status and over-limit AI-turn blocking with audit events.
- Audit logs.
- Operator console UI and WebSocket foundation.
- Analytics UI/build path.
- Local/mock provider paths.

## Working in test/mock mode

- LLM behavior when no real provider is configured.
- Voice preview/call simulation paths.
- Twilio and Asterisk service code without real trunk verification.
- YooKassa provider code without sandbox webhook verification.
- Telegram/VK/WhatsApp adapter paths and setup diagnostics without live tokens.
- RAG retrieval and local golden-case eval API/UI without full production Qdrant stack verification in this pass.
- Missing Qdrant collection fallback returns empty context with INFO-level logging, not repeated ERROR logs.

## Requires real credentials

- `OPENAI_API_KEY` or real local `VLLM_BASE_URL`.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` or Asterisk ARI credentials.
- `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`.
- `TELEGRAM_BOT_TOKEN`.
- VK/WhatsApp channel tokens, app/secret values and webhook public URLs.
- iiko/AmoCRM credentials.
- Production domains and TLS email: `APP_DOMAIN`, `API_DOMAIN`, `GRAFANA_DOMAIN`, `ACME_EMAIL`.

## Requires production infrastructure

- Docker or equivalent container runtime.
- PostgreSQL with backups and restore drill.
- Redis for rate limits/queues.
- Qdrant for vector search.
- Object storage for uploads/recordings.
- Public HTTPS domains.
- Monitoring and alert routing.
- Secrets manager or locked-down deployment secrets.

## Known limitations

- Docker stack is unverified on the current workstation.
- No real voice latency/SLO proof yet.
- No real phone/SIP call proof yet.
- No real payment webhook proof yet.
- Testbed publish gate now exposes a readiness API/UI with `100%` pass-rate requirement, latest-run summaries and publish-block details. Advanced scenario suites, per-node assertions and CI quality gates are still incomplete.
- RAG eval now checks expected source titles, expected terms, citation presence and no-answer behavior through a tenant-scoped API and knowledge-page UI. Larger golden datasets, CI threshold enforcement and production Qdrant eval evidence are still incomplete.
- Runtime guardrails now enforce the main safety path in local/mock mode, persist contact suppressions and contact consents, and expose per-tenant and per-channel policy controls with regression tests. Channel policies now block runaway auto replies, append opt-out notices for allowed messaging auto replies and can require active consent before outbound operator sends or voice calls. Larger red-team datasets and live-provider compliance proof are still incomplete.
- Security workflow is now configured to fail on Bandit, Safety and npm audit findings; it still needs proof from a green GitHub Actions run.

## Next 10 improvements with maximum impact

1. Verify full Docker local and production compose on a clean host.
2. Verify blocking security scans in GitHub Actions.
3. Expand Testbed standards with larger scenario suites, per-node assertions and CI quality checks.
4. Expand guardrails with provider-specific consent templates, larger red-team regression datasets and live-provider proof.
5. Verify one real telephony provider end-to-end.
6. Verify one real messaging channel end-to-end.
7. Verify YooKassa sandbox lifecycle.
8. Expand RAG eval datasets, CI thresholds and quality trend history.
9. Add observability alerts and run incident drill.
10. Add backup/restore drill evidence to CI or staging checklist.
