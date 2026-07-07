# Project audit (2026-07-07)

CallForce is a monorepo for an AI omnichannel sales and support SaaS: FastAPI backend, Next.js frontend, shared TypeScript packages, PostgreSQL/Redis/Qdrant/MinIO infrastructure, CI workflows, observability config, migrations, tests and runbooks.

This audit follows the production-readiness objective from the attached brief: do not call the product done unless the claim is proven by working code, tests, infrastructure and documented limitations.

## What already exists

- Monorepo structure: `apps/api`, `apps/web`, `packages/shared-types`, `packages/ui`, `infra`, `migrations`, `scripts`, `docs`.
- Backend: FastAPI, Pydantic settings, SQLAlchemy store, in-memory fallback, JWT/refresh sessions, RBAC, MFA, audit logs, API keys, team settings, billing ledger, knowledge/RAG services, parsers, action engine, scenario engine, guard rails, LLM router, speech/voice services, Twilio/Asterisk/YooKassa/iiko/AmoCRM/channel adapters.
- Frontend: Next.js app router, landing, auth, onboarding, dashboard, agents, pathway builder, knowledge, conversations, operator console, analytics, billing, settings, test console, widget, legal/status pages.
- Data: Alembic migrations with current head `6b7c8d9e0f12`, SQLAlchemy models, demo seed.
- Infrastructure: local and production Docker Compose, Traefik, PostgreSQL, Redis, Qdrant, MinIO, Prometheus, Alertmanager, Grafana, postgres backup container.
- QA: backend unit/contract/integration-style tests, Playwright browser smoke tests, lint/typecheck/build scripts, Bandit/Safety/npm audit checks.
- CI/CD: GitHub workflows for CI, QA, security, staging and deploy.
- Documentation: README, strategy pack, runbooks, architecture overview, smoke/migration/backup runbooks.

## What was verified locally

Latest verified checkpoint: 2026-07-07.

- Backend lint: `python -m ruff check app tests` passed.
- Backend typing: `python -m mypy app --show-error-codes` passed, 81 source files.
- Backend tests: `python -m pytest` passed, 138/138 tests.
- Backend security: `python -m bandit -q -r app` passed.
- Python dependency scan: `python -m safety check --full-report` passed, 0 vulnerabilities.
- Frontend lint: `npm run lint` passed.
- Frontend typing: `npm run typecheck` passed.
- Frontend build: `npm run build` passed, 35 Next.js routes.
- JS workspace tests: `npm test` passed.
- JS dependency scan: `npm audit --audit-level=moderate` passed, 0 vulnerabilities.
- Browser smoke: `npx playwright test --reporter=list` passed, 11/11 tests.
- Runtime smoke: API responds at `/api/v1/health`; web responds at `http://127.0.0.1:3000`.
- Migration state: `alembic heads` reports one head, `6b7c8d9e0f12`.
- Integration readiness: tenant-scoped API/UI checklist reports missing provider settings without exposing secret values.
- Channel webhook diagnostics: tenant-scoped API/UI shows Telegram/VK/WhatsApp callback URLs, HTTPS status, missing settings and security warnings without exposing tokens/secrets.
- RAG fallback: missing Qdrant collection now returns empty context with a single INFO log instead of repeated ERROR noise.
- RAG eval: tenant-scoped golden-case API/UI checks expected source titles, expected answer terms, citation presence and no-answer behavior without requiring live Qdrant/OpenAI.
- Billing limits: monthly message limits have one backend source of truth, billing status reports remaining/period/exceeded state, and over-limit AI turns are blocked with `402 BILLING_LIMIT_REACHED` plus audit log.
- Testbed readiness: agent-level readiness API/UI reports `100%` required pass rate, latest run summaries, missing/stale/running/failed counts and publish-block details.

## What is broken or unverified

- Docker is not installed on the current workstation, so `docker compose config`, full local compose startup and production compose startup were not verified in this pass.
- Real PostgreSQL/Redis/Qdrant/MinIO runtime was not verified locally in this pass because compose could not run.
- Real telephony is not proven: Twilio/Asterisk/SIP paths have code and tests, but no real phone number/SIP trunk call was completed.
- Real STT/TTS latency is not proven: provider abstractions exist, but streaming production latency, barge-in and transcript quality need real credentials and call tests.
- Real YooKassa payment/subscription lifecycle is not proven end-to-end with sandbox credentials.
- Telegram/VK/WhatsApp adapters and setup diagnostics exist, but real external webhook verification and message delivery were not proven with live tokens in this pass.
- RAG has parsers/chunking/embedding/Qdrant-ready pieces, graceful empty-index fallback and a local golden-case eval API/UI for citations/no-answer checks, but production Qdrant ingestion evidence, larger datasets and CI threshold history are not yet enough to claim enterprise quality.
- Security workflow has been changed to run blocking Bandit, Safety and npm audit checks; the next required proof is a green GitHub Actions run on the target branch.
- Several user-facing docs and pages are present, but some older docs show mojibake in PowerShell output due console encoding. Browser rendering should still be checked for all Russian pages.

## Missing production capabilities

P0 gaps before a real paid pilot:

- Container stack verification on a clean machine.
- Real external credentials smoke: OpenAI or local vLLM, YooKassa sandbox, at least one messaging channel, at least one telephony provider. Tenant-scoped readiness checklist now shows the missing setup before launch, but live credentials still must be verified.
- Advanced Testbed standards: publish gate now blocks missing, failed, running or stale scenario runs and exposes pass-rate readiness summaries, but larger scenario suites, per-node tests and CI eval history still need expansion.
- Runtime guard rails are partially enforced: opt-out intent, human handoff intent, regulated topics, unsafe outbound claims, unsafe tool calls and missing order confirmation now produce audit events and forced escalation. Durable contact suppression/do-not-call storage exists and blocks outbound calls/operator sends for suppressed contacts. Durable contact consent storage exists, supports expiry/revoke, has API create/list/revoke and can be required by channel policy for outbound operator sends and voice calls. Per-tenant guardrail policy API/UI, per-channel automation policy API/UI, auto-reply caps, opt-out notice injection and initial red-team regression tests exist. Remaining work: larger red-team eval datasets and live-provider compliance evidence.
- Billing payment lifecycle: message limits are now enforced, but YooKassa sandbox subscription/payment webhook reconciliation and invoice evidence still need a real-provider pass.
- Observability cockpit: alerts for failed calls, failed payments, high latency, webhook failure rate and queue backlog.
- Backup/restore drill with real database volume and documented RPO/RTO.

P1 gaps:

- Memory/contact identity merge across channels.
- Human handoff state machine with operator SLA and call bridge.
- Larger RAG golden datasets, CI no-answer/citation thresholds and quality trend history.
- Complete channel setup wizards for email/generic webhook and live-provider webhook smoke evidence for Telegram/VK/WhatsApp.
- CRM pipeline and lead recovery workflows beyond adapters/contracts.
- Load testing with realistic concurrency and call/chat traffic.

P2 gaps:

- SSO/SAML/OIDC.
- Data retention/export/delete workflows for compliance.
- Marketplace/integration gallery.
- Advanced AI supervisor quality scoring and weekly growth report automation.
- Multi-region or self-hosted deployment guide.

## Architecture choice

Keep the current modular monorepo architecture:

- FastAPI backend as the system of record and integration boundary.
- SQLAlchemy/PostgreSQL for durable tenant data.
- Redis for rate limits, queues and ephemeral coordination.
- Qdrant for vector search.
- Object storage for uploaded knowledge and call recordings.
- Provider interfaces for LLM, STT, TTS, telephony, messaging, CRM, billing and storage.
- Next.js frontend as the SaaS workspace and public product surface.
- Docker Compose for single-node production/staging, with a future path to Kubernetes only after real load requires it.

This is the safest path because it preserves existing tests and modules while giving clear seams for real providers.

## Priority roadmap

P0:

1. Install Docker on a clean machine and verify `infra/docker-compose.local.yml` and `infra/docker-compose.yml`.
2. Verify the blocking security workflow in GitHub Actions.
3. Expand Testbed standards with larger scenario suites, per-node assertions and CI quality checks.
4. Expand runtime guard rails with provider-specific consent templates, larger red-team evals and live-provider compliance proof.
5. Verify one real channel webhook and one real telephony call.
6. Verify YooKassa sandbox subscription/payment webhook lifecycle.
7. Run backup/restore drill against real Postgres volume.

P1:

1. Build memory/contact identity merge.
2. Finish warm transfer state machine and operator SLA dashboard.
3. Expand RAG eval datasets, CI thresholds and quality trend history.
4. Finish remaining channel setup wizards and run real webhook diagnostics with provider sandboxes/tokens.
5. Add load tests to CI/staging.

P2:

1. Add SSO and compliance data lifecycle flows.
2. Add integration marketplace pages.
3. Add AI supervisor reports and lead recovery automation.
4. Add self-host/enterprise deployment variant.

## Definition of done

The project is production-ready only when every item below has direct evidence:

- Local and containerized startup work from a clean checkout.
- Backend/frontend/security/browser gates pass locally and in CI.
- Database migrations run forward on an empty and existing database.
- A user can register, create an organization, invite a team member, create an agent, upload knowledge, test it, publish it, receive a customer message, hand off to an operator and see analytics.
- At least one messaging channel works with real credentials.
- At least one real voice call works with transcript, summary, handoff fallback and measured latency.
- Billing sandbox works with subscriptions, webhooks, limits and ledger reconciliation.
- Backup and restore are tested.
- Monitoring and alerts catch critical failures.
- All production limitations are documented.
