# 09. Master checklist to ideal working system

## Product and market

- [ ] Industry presets for restaurants, clinics, e-commerce and services.
- [x] Local restaurant demo tenant for sales and onboarding.
- [ ] Pilot execution kit implemented in product and operations.
- [ ] Finalize ICP and first vertical.
- [ ] Create landing page.
- [x] Create ROI calculator.
- [ ] Create pitch deck.
- [ ] Create pilot offer and contract template.
- [ ] Create demo script and video.
- [ ] Build first 3 case studies.

## Backend

- [x] FastAPI skeleton.
- [x] Core MVP endpoints.
- [x] SQLAlchemy repository foundation.
- [x] RAG ingestion skeleton.
- [x] JWT/RBAC/audit foundation.
- [x] Auth-bound business route tenant guard with local legacy fallback.
- [x] Local production service endpoints.
- [x] Production JWT/refresh/session revocation.
- [x] Basic MFA setup/login/recovery codes/disable with public user redaction.
- [x] Local OpenAI-compatible/vLLM routing without OpenAI key.
- [x] Voice preview turn with session transcript and conversation logging.
- [ ] PostgreSQL default runtime for staging/prod.
- [ ] Alembic migrations.
- [ ] Redis queue workers.
- [ ] Real Qdrant upsert/search.
- [ ] Real Telegram webhook.
- [x] Real VK webhook with community message handling and confirmation.
- [x] Real WhatsApp webhook with Meta validation and message handling.
- [x] Web widget API with persistent session conversation and browser smoke.
- [x] Real iiko adapter with menu sync and order creation using iikoCloud API.
- [ ] Real YooKassa redirect + webhooks.
- [ ] SIP/Asterisk voice path.
- [ ] Billing plans and usage metering.
- [ ] Analytics event pipeline.

## Frontend

- [ ] Preset chooser UI.
- [ ] Demo tenant switcher for sales calls.
- [x] ROI calculator page.
- [x] Next.js MVP shell.
- [x] Dashboard pages.
- [x] Mock/live API fallback.
- [x] Production readiness section.
- [ ] Public marketing site.
- [ ] Onboarding wizard.
- [x] Agent creation UI through Core API.
- [x] Agent edit/publish/test UI through Core API.
- [x] Knowledge source creation UI through Core API.
- [x] Test console through Core API mock chat.
- [x] Account security settings, MFA setup, recovery codes and disable UI.
- [ ] Full agent builder validation/edit/publish flow.
- [x] Knowledge upload ingestion states.
- [x] Embedded web widget page and launcher wired to Core API.
- [x] Text voice preview in test console wired to Core API.
- [ ] Operator inbox.
- [x] Analytics dashboards.
- [ ] Billing/settings UI.
- [ ] Design system/storybook.

## AI/RAG quality

- [x] Chunking/retrieval helper.
- [x] Source attribution.
- [x] No-answer policy skeleton.
- [x] LLM provider routing for local vLLM/OpenAI/mock.
- [ ] Embedding provider abstraction.
- [ ] Reranker.
- [ ] Golden dataset per tenant.
- [ ] Automated eval in CI/staging.
- [ ] Prompt injection tests.
- [ ] Unresolved topic recommendations.

## Security/compliance

- [x] PII masking foundation.
- [x] RBAC foundation.
- [x] Audit event schemas.
- [x] MFA secret redaction from public auth responses.
- [x] MFA recovery codes stored hashed and consumed as single-use codes.
- [ ] Formal threat model.
- [ ] Privacy policy.
- [ ] Consent templates.
- [ ] Roskomnadzor notification analysis.
- [ ] RF data hosting plan.
- [ ] Retention/delete/export flows.
- [ ] Secret manager integration.
- [ ] Security questionnaire.
- [x] Incident response runbook.

## QA/DevOps

- [x] Lint/typecheck/test/build/audit/pre-commit.
- [x] Auth/MFA recovery/disable regression tests.
- [x] Knowledge upload/ingestion regression and browser smoke.
- [x] Web widget API regression and browser smoke.
- [x] Voice preview regression tests.
- [x] GitHub Actions skeleton.
- [x] Runbooks.
- [ ] Staging environment.
- [ ] Preview deployments.
- [x] E2E Playwright tests.
- [ ] Load tests.
- [ ] Backup restore drill automation.
- [x] Monitoring/alerts.
- [ ] Release checklist.

## Sales/customer success

- [ ] Unit economics dashboard.
- [ ] Pilot report generator.
- [ ] Audit-to-pilot sales workflow.
- [ ] CRM pipeline.
- [ ] Lead scoring.
- [ ] Demo tenant templates by industry.
- [ ] Pilot onboarding checklist.
- [ ] Weekly report template.
- [ ] Customer success playbook.
- [ ] Partner/integrator program.

## Definition of ideal v1

The system is “ideal v1” when:

- a real customer can sign up or be onboarded by admin;
- Telegram + web widget work in production;
- knowledge ingestion uses real Qdrant;
- AI answers only with sources or escalates;
- operator can take over;
- iiko/YooKassa work for at least one pilot vertical;
- dashboard shows ROI and quality;
- data is stored in compliant RF setup;
- staging/prod deploys are repeatable;
- all critical flows have automated tests and runbooks.
