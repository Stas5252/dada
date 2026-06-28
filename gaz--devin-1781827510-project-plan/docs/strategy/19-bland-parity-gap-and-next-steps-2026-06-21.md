# 19. Bland parity gap and next steps (2026-06-21)

This document is the current execution checkpoint for turning CallForce into a Bland.ai-level product and then surpassing it for the Russian SMB market.

## Current verified state

After the 2026-06-21 hardening pass, the project has a clean technical baseline again:

- Backend lint: `ruff check apps/api/app apps/api/tests` passed.
- Backend typing: `mypy app` passed for 69 source files.
- Backend tests: `pytest` passed, 105/105 tests.
- Frontend lint: `npm run lint` passed with 0 errors and 23 warnings.
- Frontend/workspace typing: `npm run typecheck` passed.
- Production build: `npm run build` passed.
- Workspace JS tests: `npm test` passed; no workspace test scripts are currently defined.

Code issues fixed in this pass:

- Removed a broken duplicate demo request endpoint that referenced missing dependencies/models.
- Restored backend type safety in agents/pathway validation, iiko settings handling, parser retry errors, job workers, service factories, billing IDs, scenario interpretation, and action engine tool payload parsing.
- Fixed frontend type errors in the visual pathway editor and ROI calculator.
- Restored readable Russian responses in the scenario/action execution layer where touched.

## Bland benchmark signals used

Official Bland materials position Bland as a voice AI platform for regulated industries with production agent building, scenario testing, deployment across Voice/SMS/iMessage/Web Chat, unified memory, live QA/observability, enterprise integrations, low-latency voice, SIP/telephony support, guard rails, testbed standards, warm transfer, compliance, and self-host/on-prem options.

Key sources reviewed:

- https://www.bland.ai/
- https://docs.bland.ai/welcome-to-bland
- https://docs.bland.ai/llms.txt
- https://docs.bland.ai/tutorials/pathways
- https://docs.bland.ai/tutorials/guard-rails
- https://docs.bland.ai/tutorials/memories
- https://docs.bland.ai/enterprise-features/SIP-integration
- https://docs.bland.ai/tutorials/warm-transfer

## Honest parity matrix

| Area | Current CallForce state | Bland-level target | Gap |
| --- | --- | --- | --- |
| Visual agent builder | Pathway editor, save/load API, basic validation, scenario interpreter | Node/edge builder with unit tests, scenario simulation, version diff, publish gates | Add Testbed-style standards, per-node tests, versioned publish workflow |
| Guard rails | Prompt policy validator and action confirmations | Continuous conversation guard rails for opt-out, policy, safety, transfer | Add runtime guardrail engine with audit events and blocking/escalation actions |
| Memory | Customer/conversation persistence, summaries foundation | Cross-channel contact facts, recent messages, open items, automatic updates | Add explicit memory store/read/update API and UI |
| Voice | Text voice preview, Twilio hooks, voice session transcript | Real-time SIP/Twilio/Asterisk call path with streaming STT/TTS and latency SLO | Build SIP trunk UI, ARI bridge, streaming pipeline, latency telemetry |
| Warm transfer | Operator escalation/inbox foundation | AI briefs human, calls/merges human agent, tracks transfer states | Add transfer state machine and phone bridge |
| Channels | Widget, Telegram, VK, WhatsApp backend pieces, iiko | Production setup wizards and identical routing across channels | Finish WhatsApp/VK UI setup, secrets, webhook verification UX |
| RAG quality | Chunking, sources, Qdrant-ready work, parser coverage | Eval lab, citations, no-answer enforcement, regression datasets | Add golden datasets, CI eval, per-tenant quality dashboard |
| Billing | Usage ledger foundation and billing UI pieces | Plans, limits, invoices/subscriptions, payment webhooks | Finish YooKassa subscriptions, tenant limits, usage enforcement |
| Observability | Health/readiness, audit, logging/monitoring pieces | Live QA, traces, call logs, alerts, replay/debug tools | Add conversation/call QA dashboard and SLO alerts |
| Enterprise/security | JWT/RBAC/MFA/audit foundations | SSO, retention/export/delete, compliance docs, self-host runbook | Add threat model, retention flows, RF hosting plan, SSO roadmap |

## Next execution order

1. Gate hygiene cleanup: remove frontend lint warnings, fix Recharts SSR width warnings, add smoke coverage for ROI/pathway pages.
2. Bland-style Testbed: scenario standards, pass threshold, per-node test runs, publish gating, run history.
3. Runtime guard rails: opt-out, prohibited content, forced escalation, tool-call safety, audit trail.
4. Cross-channel memory: contact facts, conversation summaries, open items, channel identity merge, memory UI.
5. Real voice/SIP MVP: SIP trunk settings UI, Asterisk/ARI inbound, streaming STT/TTS, state machine execution, latency metrics.
6. Warm transfer: human destination settings, AI briefing, transfer states, operator/call handoff logs.
7. Production monetization: YooKassa subscriptions, plan limits, usage metering, billing alerts.
8. Launch readiness: staging deploy, load tests, backup/restore drill, security threat model, RF data hosting plan.

## Acceptance bar before saying "10000% done"

Do not call the project finished until all of these pass:

- Full backend gates pass: ruff, mypy, pytest.
- Full frontend gates pass: lint with no errors, typecheck, production build.
- Browser smoke covers landing, register/login, dashboard, agent builder, pathway testbed, knowledge ingestion, widget, operator handoff, billing, and voice preview.
- At least one real pilot flow works end-to-end: signup/onboard -> connect channel -> upload knowledge -> test scenarios -> publish -> customer conversation -> operator takeover -> order/payment or CRM action -> analytics.
- Voice path is tested on a real number/SIP trunk with measured latency and transcript quality.
- Billing, limits, audit, backup/restore, monitoring alerts, and runbooks are verified in staging.

## Immediate next slice recommendation

The highest-leverage next implementation slice is Bland-style Testbed + Guard Rails, before deeper voice work. It improves agent quality for every channel and gives a visible enterprise feature: run scenarios, enforce standards, block unsafe flows, and only publish agents when tests pass.
