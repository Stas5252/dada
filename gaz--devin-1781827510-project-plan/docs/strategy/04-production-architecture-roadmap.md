# 04. Production architecture roadmap

## Целевая архитектура

```text
Channels
  Telegram / Web Widget / SIP-Asterisk / Email-API
      |
API Gateway + Tenant Context + Auth/RBAC
      |
Conversation Orchestrator
      |-- RAG Retrieval Service -> Qdrant + Knowledge DB
      |-- LLM Gateway -> model routing, safety, caching
      |-- Action Engine -> integrations/tools with audit/idempotency
      |-- Handoff Service -> human inbox/operator routing
      |
PostgreSQL: tenants, users, agents, conversations, messages, billing, audit
Redis: queues, sessions, rate limits, locks
Object Storage: files, transcripts, exports
Observability: logs, metrics, traces, eval reports
```

## Основные bounded contexts

1. **Identity & Tenant**
   - tenants, users, memberships, roles;
   - SSO later;
   - audit events.
2. **Agent Runtime**
   - agent versions;
   - published configs;
   - prompts/procedures/guardrails;
   - rollback.
3. **Conversation Runtime**
   - message ingestion;
   - context memory;
   - state machine;
   - handoff.
4. **Knowledge/RAG**
   - sources, chunks, embeddings;
   - indexing jobs;
   - retrieval/reranking;
   - evaluation.
5. **Action Engine**
   - contracts;
   - tool registry;
   - permissions;
   - confirmations;
   - idempotency;
   - retries;
   - audit.
6. **Billing**
   - plans;
   - usage metering;
   - payments;
   - invoices;
   - idempotency.
7. **Analytics**
   - events;
   - dashboards;
   - unresolved topics;
   - quality metrics.

## Deployment targets

### Local

Docker Compose: PostgreSQL, Redis, Qdrant, MinIO, API, web.

### Staging

- managed PostgreSQL in РФ;
- managed/object storage in РФ;
- Qdrant managed/self-hosted in РФ;
- separate secrets;
- public HTTPS;
- smoke tests after deploy.

### Production

- multi-AZ database;
- backup + restore drill;
- autoscaling API/web/workers;
- rate limits;
- WAF/reverse proxy;
- audit log immutability;
- SLO dashboards;
- incident process.

## Roadmap phases

### Phase 1: Production MVP

- enable `STORE_BACKEND=sqlalchemy` by default for non-local;
- Alembic migrations or hardened SQL runner;
- real Telegram bot webhook;
- web widget JS embed;
- production RAG ingestion with Qdrant;
- hosted staging.

### Phase 2: Paid pilot readiness

- onboarding wizard;
- operator inbox;
- golden set evaluator;
- admin analytics;
- usage metering;
- security/privacy docs;
- customer success playbook.

### Phase 3: Real integrations

- iiko production adapter;
- YooKassa redirect payments, no card data stored;
- SIP/Asterisk voice path;
- CRM/webhook connector;
- retry/dead-letter queues.

### Phase 4: Scale and enterprise

- SSO/SAML;
- team permissions;
- data retention per tenant;
- exports;
- private cloud/on-prem option;
- SLA and support tiers.

## Non-negotiable production requirements

- every request has tenant context;
- every external action has idempotency key;
- every destructive action requires confirmation;
- every AI answer has sources or no-answer escalation;
- every provider secret is in secret manager, never in git;
- every deploy has rollback;
- every release has smoke/eval results.
