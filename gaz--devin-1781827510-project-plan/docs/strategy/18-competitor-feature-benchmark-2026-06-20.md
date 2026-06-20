# 18. Competitor feature benchmark: AI support and voice agents

Date checked: 2026-06-20.

This benchmark uses official product/documentation pages where possible. It is
not a pricing scrape; it is a product-readiness checklist for what CallForce
must match before it can be honestly described as production-grade.

## Sources checked

- Intercom / Fin: https://www.intercom.com/ and https://fin.ai/
- Intercom Fin help: https://www.intercom.com/help/en/articles/7120684-fin-ai-agent-explained
- Zendesk AI Agents: https://www.zendesk.com/service/ai/ai-agents/
- Zendesk AI Agents help: https://support.zendesk.com/hc/en-us/articles/6970583409690-About-AI-agents
- Ada: https://www.ada.cx/ and https://www.ada.cx/platform/
- PolyAI: https://poly.ai/ and https://poly.ai/guides/call-center-voice-ai
- Retell AI: https://www.retellai.com/ and https://docs.retellai.com/general/introduction
- Bland AI: https://www.bland.ai/ and https://docs.bland.ai/welcome-to-bland
- Five9 AI Agents: https://www.five9.com/products/capabilities/ai-agents

## What top competitors make feel "ideal"

| Area | Competitor expectation | CallForce current status |
| --- | --- | --- |
| Build/test/deploy/monitor loop | Retell positions this explicitly for phone agents; enterprise support vendors expose setup, testing and monitoring as one flow. | Partial. Test console, chat, widget and voice preview exist. Production monitoring/evals are still open. |
| Omnichannel continuity | Zendesk/Ada/Fin market chat, email, messaging, phone and handoff with context continuity. | Partial. Widget, Telegram path and Twilio/SMS skeletons exist; WhatsApp/email/operator continuity still open. |
| Knowledge-grounded answers | Fin/Ada/Zendesk emphasize AI agents over support content and workflows. | Skeleton/partial. Local chunking and attribution exist; real Qdrant upsert/search and evals are still open. |
| Human handoff | Intercom/Fin and Five9 emphasize handoff to human teams with context. | Skeleton. Tool call can return handoff text; real operator inbox/queue is open. |
| Voice quality | PolyAI/Bland/Retell emphasize natural voice, low latency, monitoring and telephony. | Not production-complete. Text voice preview, WebSocket audio and Twilio webhook exist; real SIP/STT/TTS quality, barge-in and recordings are open. |
| Guardrails and control | Enterprise vendors sell governance, multilingual control, compliance, analytics and safety. | Partial. RBAC/MFA/audit foundations exist; prompt-injection evals, retention/export/delete and formal threat model are open. |
| Workflow actions | Zendesk/Five9/Ada position agents that can execute tasks in authorized systems. | Skeleton. iiko/YooKassa/webhook contracts and local adapters exist; real connectors and action runtime are open. |
| Outcome analytics | Competitors highlight resolution rate, automation rate, savings and quality metrics. | Partial. Dashboard counts exist; ROI, CSAT, quality score, voice latency and cost dashboards are open. |

## P0 parity gaps before paid pilots

- Real Qdrant-backed retrieval with source-only answer policy and no-answer evals.
- Operator inbox/handoff with summary, transcript, customer context and close reason.
- Real Telegram webhook hardening and production web widget installation flow.
- iiko and YooKassa production sandbox/live paths with idempotent webhooks.
- Staging deployment with PostgreSQL default, migrations, backup/restore and monitoring.
- Security/privacy basics: threat model, privacy policy, consent text, retention/delete/export.

## P0 voice gaps before selling phone agents

- One selected telephony path for MVP: Twilio for global demo or SIP/Asterisk for RF provider integration.
- Streaming STT/TTS adapter with latency budget and fallback behavior.
- Barge-in/interruption behavior and test harness.
- Call recordings, transcript timestamps, retention policy and consent language.
- Voice latency metrics: STT, LLM, TTS, total turn time, failure rate.
- 5-10 real end-to-end test calls with logs before any customer promise.

## What was closed in the 2026-06-20 pass

- Added authenticated `POST /api/v1/voice/sessions/{session_id}/preview-turn`.
- Voice preview now runs the voice orchestrator path, updates `VoiceSession.transcript`, records a conversation log and returns `conversation_id`.
- Existing audio, Twilio voice webhook and WebSocket voice stream now record voice session turns.
- Fixed outbound Twilio webhook URL to include `/api/v1/voice/webhooks/...`.
- Added `twilio_voice` and `speech_stt_tts` readiness providers.
- Added text Voice preview in `/test-console`.

## Honest positioning

CallForce can be presented as a strong local MVP foundation for AI chat support
with a voice-preview/testing layer. It should not yet be sold as equivalent to
Retell, Bland, PolyAI or enterprise Zendesk/Ada/Fin voice automation until real
telephony, speech, monitoring and operator handoff are proven end to end.
