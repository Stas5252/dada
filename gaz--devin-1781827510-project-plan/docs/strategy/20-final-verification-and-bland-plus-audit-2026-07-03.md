# 20. Финальная сверка после больших изменений и план Bland+ (2026-07-03)

Этот документ фиксирует состояние проекта после повторного аудита кода, тестов,
security-гейтов и браузерных сценариев. Цель прежняя: не просто догнать
Bland.ai, а сделать более удобную платформу для русскоязычного SMB/enterprise:
голос, чат, RAG, операторы, биллинг, каналы, интеграции и контроль качества в
одном рабочем продукте.

## Короткий честный вывод

Проект стал заметно сильнее и сейчас проходит основные локальные quality gates.
Но слово "готово на 10000%" можно говорить только после staging/prod-проверки с
реальными внешними сервисами: SIP/Twilio/Asterisk, STT/TTS, YooKassa,
PostgreSQL/Redis/Qdrant/S3, мониторингом, backup/restore и пилотным клиентским
сценарием от регистрации до оплаты/заказа/операторского handoff.

## Что проверено локально

Дата проверки: 2026-07-07.

Backend:

- `python -m ruff check app tests` - passed.
- `python -m mypy app --show-error-codes` - passed, 81 source files.
- `python -m pytest` - passed, 138/138 tests.
- `python -m bandit -q -r app` - passed, no issues.
- `python -m safety check --full-report` - passed, 0 vulnerabilities.

Frontend/workspace:

- `npm run lint` in `apps/web` - passed.
- `npm run typecheck` in `apps/web` - passed.
- `npm run build` in `apps/web` - passed, Next.js production build generated 35 routes.
- `npm test` from repository root - passed; no workspace test scripts are currently defined.

Browser E2E:

- Local API started on `http://127.0.0.1:8000`.
- API health checked at `/api/v1/health`.
- `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npx playwright test --reporter=list` - passed, 11/11 tests.
- Covered smoke flows: landing, login, register, legal pages, ROI calculator, billing checkout, onboarding, chat simulation, Testbed CRUD/readiness, RAG eval UI.

Known local environment limitation:

- Docker CLI is not installed on this workstation, so `docker compose config` and full container-stack verification were not run in this pass.

## Исправления в этом проходе

Quality and typing:

- Restored strict backend typing in parser URL validation, billing service helpers, RAG embeddings, voice/orchestrator paths, Asterisk ARI, operator WebSocket broadcast, Twilio import handling and YooKassa confirmation URL handling.
- Normalized OpenAI TTS `response_format` to allowed literal values before API calls.
- Removed unused frontend imports and fixed React escaped text violations on the landing page.
- Fixed ROI calculator build-time Recharts sizing warning by rendering the chart only after client mount.
- Removed empty `catch (e)` patterns in the operator console.

Security:

- Upgraded backend dependencies to remove known Starlette vulnerability:
  - `fastapi==0.139.0`
  - `starlette>=1.0.1`, resolved to `1.3.1`
  - `prometheus-fastapi-instrumentator>=8.0.2`
  - `pytest>=9.0.3`, resolved to `9.1.1`
- Replaced non-cryptographic VK webhook random IDs with `secrets.randbelow`.
- Removed runtime `assert` usage from request/response handling paths.
- Cleaned Bandit false positives for audit event names and local demo fixtures.
- Replaced damaged `ACCESS_TOKEN_SECRET` warning text with readable ASCII log output.
- Added graceful RAG fallback for a missing Qdrant collection: empty context is returned with INFO-level logging instead of repeated ERROR logs.
- Added billing limit enforcement: one monthly message-limit source of truth, billing status remaining/exceeded fields, `402 BILLING_LIMIT_REACHED` blocking and audit logging.
- Added channel webhook diagnostics: Telegram/VK/WhatsApp callback URLs, HTTPS readiness, missing settings and security warnings without returning secret values.
- Added Testbed readiness: agent-level pass-rate summaries, latest run summaries, missing/stale/running/failed counts and publish-block details.
- Added RAG eval API/UI: tenant-scoped golden checks for expected source titles, expected answer terms, citation presence and no-answer behavior.

## Bland.ai benchmark used

Official sources reviewed:

- https://www.bland.ai/
- https://docs.bland.ai/welcome-to-bland
- https://docs.bland.ai/llms.txt
- https://docs.bland.ai/tutorials/testbed
- https://docs.bland.ai/tutorials/warm-transfer

Main Bland-level capabilities to match or beat:

- production voice AI agents;
- visual agent logic and testing;
- Testbed-style scenario standards;
- guard rails and safety controls;
- warm transfer to humans;
- unified memory;
- telephony/SIP support;
- logs, observability and QA;
- enterprise integrations and compliance posture.

## Current parity snapshot

| Area | Current state | Bland+ target | Remaining gap |
| --- | --- | --- | --- |
| Testbed | CRUD, e2e smoke, readiness API/UI, `100%` pass-rate publish gate and latest-run summaries exist | Scenario suites, per-node assertions, publish gates, CI eval history | Expand larger scenario suites, per-node checks and CI eval gates |
| Guard rails | Runtime opt-out, durable DNC/contact suppression, durable contact consent ledger with expiry/revoke, consent-required outbound blocking, handoff intent, regulated topic escalation, unsafe outbound claim blocking, unsafe tool-call blocking, per-tenant policy API/UI, per-channel automation policy API/UI, auto-reply caps, opt-out notice injection, initial red-team regression and audit events exist | Larger eval suites, provider-specific consent templates and live-provider compliance proof | Add larger red-team datasets, provider consent templates and live-provider proof |
| Voice | Twilio/Asterisk/ARI/STT/TTS foundations exist | Real streaming calls with latency SLO and call QA | Verify real SIP/phone call end-to-end |
| Warm transfer | Operator console and handoff pieces exist | AI brief, call merge/transfer state machine, operator SLA | Finish phone bridge and transfer lifecycle |
| Memory | Conversation/user storage exists | Cross-channel contact memory and automatic updates | Add memory API/UI and identity merge |
| RAG | Parsers/chunking/Qdrant-ready flow, graceful missing-collection fallback and tenant-scoped eval API/UI for citations/no-answer checks exist | Larger eval datasets, CI thresholds, production Qdrant evidence, quality trends | Add larger golden datasets and CI eval history |
| Billing | Ledger/YooKassa/provider pieces, monthly message-limit status and over-limit AI-turn blocking exist | Subscriptions, invoices, webhook reconciliation, plan-change evidence | Verify real YooKassa sandbox and webhook reconciliation |
| Observability | Health/readiness/audit/logging exist | Live QA, traces, alerts, replay/debug for calls/chats | Add dashboards, SLO alerts and incident drill |
| Channels | Widget/Telegram/VK/WhatsApp foundations, tenant-scoped launch readiness checklist and webhook diagnostics exist | Full setup wizards, verified live webhooks, identical routing | Finish email/generic setup and real channel sandbox tests |
| Compliance | JWT/RBAC/MFA/audit foundations exist | Retention/export/delete, RF hosting plan, SSO roadmap | Threat model and data lifecycle controls |

## Next execution order

1. Expand the enforced Testbed gate: larger scenario suites, per-node assertions and CI quality checks.
2. Expand runtime guard rails: provider-specific consent templates, larger red-team regression datasets and live-provider compliance proof.
3. Add memory store and UI: facts, recent messages, open tasks, per-channel identity merge.
4. Run a real voice pilot: Asterisk/SIP or Twilio number, streaming STT/TTS, measured latency, transcript quality.
5. Finish warm transfer: AI summary, operator destination, bridge/merge flow, transfer states and logs.
6. Finish billing proof: YooKassa sandbox, subscription webhook reconciliation, invoices and real plan-change evidence.
7. Expand RAG eval lab: larger golden datasets, CI regression threshold and quality trend history.
8. Add observability cockpit: traces, call/chat replay, failed action alerts, latency and cost dashboards.
9. Run staging deploy with real Postgres/Redis/Qdrant/object storage and backup/restore drill.
10. Run one pilot business flow end-to-end: signup -> channel -> knowledge -> testbed -> publish -> live conversation -> operator/payment/order -> analytics.

## Acceptance bar before "10000% done"

The project is not finished until all of these are true:

- backend, frontend, security and browser gates pass in CI and locally;
- containerized staging stack starts from a clean machine;
- one real phone/SIP path is tested, recorded and measured;
- one real payment/subscription path is tested in sandbox;
- one real channel webhook path is tested outside mocks;
- Testbed and guard rails block unsafe/broken agent publishing;
- backup/restore drill is documented and verified;
- observability alerts catch failed calls, failed payments and high latency;
- documentation explains setup, support, recovery and launch operations;
- a pilot customer can complete the full business workflow without developer intervention.
