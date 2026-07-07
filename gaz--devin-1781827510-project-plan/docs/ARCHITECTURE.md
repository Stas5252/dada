# Architecture

## System overview

CallForce is a modular SaaS monorepo:

- `apps/api`: FastAPI backend.
- `apps/web`: Next.js frontend.
- `packages/shared-types`: shared TypeScript contracts.
- `packages/ui`: shared UI exports.
- `infra`: deployment and observability.
- `migrations`: Alembic migrations.
- `scripts`: operational scripts.
- `docs`: product, architecture and runbooks.

## Backend layers

- API routes: `apps/api/app/api/v1`.
- Auth/security: `security.py`, `rbac.py`, `tenant.py`, auth routes.
- Store/data: `store.py`, `sqlalchemy_store.py`, `db_models.py`, migrations.
- AI/RAG: `llm_router.py`, `rag.py`, `parsers.py`, `orchestrator.py`, `policy_validator.py`.
- Safety/compliance: `guard_rails.py` plus durable contact suppression/do-not-call and contact consent records in the store layer.
- Voice: `voice_service.py`, `speech_service.py`, `twilio_service.py`, `asterisk_ari_service.py`.
- Integrations: `integration_services.py`, channel adapters, iiko/AmoCRM, YooKassa.
- Observability: logging, tracing, health/readiness, Prometheus/Grafana infra.

## Frontend layers

- App router pages under `apps/web/app`.
- Server actions in `apps/web/app/actions.ts`.
- API client in `apps/web/lib/core-api.ts`.
- Auth helpers in `apps/web/lib/auth.ts`.
- Reusable workspace components under `apps/web/app/components`.
- Playwright tests under `apps/web/tests`.

## Data stores

- PostgreSQL: durable tenant/user/agent/conversation/billing data.
- Redis: rate limits, queue-ready coordination.
- Qdrant: vector search for RAG.
- Object storage: future uploads/call recordings.

## Provider boundaries

The product should keep provider interfaces for:

- LLM.
- STT.
- TTS.
- Telephony.
- Messaging channels.
- CRM.
- Calendar/booking.
- Billing.
- Storage.

Provider-specific code must stay behind adapters so CallForce can support local/SaaS/enterprise deployments without rewriting business logic.

## Production architecture direction

Single-node Docker Compose is enough for first paid pilots. Move to Kubernetes only after:

- multiple concurrent tenants require horizontal scaling;
- real voice traffic creates measurable CPU/network limits;
- Redis/Qdrant/PostgreSQL operational needs exceed compose-based operations.
