# Architecture overview

The platform is a multi-tenant SaaS system with a low-latency realtime voice path and a reliability-oriented backend path.

## Runtime paths

- Chat path: channel webhook -> `MessageEvent` normalization -> conversation state -> scenario/RAG/tool -> LLM -> response -> analytics.
- Voice path: SIP provider -> Asterisk/ARI -> audio WebSocket -> VAD/STT -> orchestrator -> RAG/tool/LLM -> streaming TTS -> RTP playback -> logs.
- Knowledge path: upload/URL/iiko sync -> extraction -> cleanup -> chunks -> embeddings -> Qdrant upsert -> validation -> active source. The MVP API currently runs the chunk/embed steps through a deterministic local stub and records an idempotent ingestion job before real Qdrant writes are enabled.
- Action path: slot collection -> validation -> explicit confirmation when required -> Action Engine -> external API -> audit log.

## Core boundaries

- `apps/api`: public REST/WebSocket boundary, auth, tenant context.
- `services/agent-core`: prompt policy, memory summary, scenario runtime.
- `services/rag-service`: ingestion, retrieval, citations, unresolved topics.
- `services/action-engine`: tool registry, schemas, policies, idempotency, audit.
- `services/voice-realtime`: SIP, audio frames, VAD/STT/TTS orchestration.
- `apps/web`: marketing site and customer dashboard.
