# 05. Backend plan to ideal production system

## Current backend foundation

Already implemented:

- FastAPI app;
- auth register/login;
- JWT access tokens with refresh rotation and logout revocation;
- tenant isolation via bearer tenant context with local `x-tenant-id` fallback;
- SQLAlchemy models and SQL-backed store;
- RAG helpers and ingestion skeleton;
- JWT/RBAC/audit foundation;
- local adapters for iiko, Telegram, YooKassa, webhooks, voice, billing;
- readiness endpoint;
- 56 backend tests.

## Backend epics

### AUTH-1: production authentication

Tasks:

- signed JWT access + refresh lifecycle is implemented;
- password reset;
- email verification;
- session revocation/logout is implemented;
- brute-force protection;
- optional TOTP for admins;
- later SSO/SAML.

Acceptance:

- refresh rotation tested;
- token revocation works;
- admin endpoints require permissions;
- audit events for login/logout/password reset.

### TENANT-1: tenant management

Tasks:

- tenant settings;
- business profile;
- timezone/language;
- data retention policy;
- channel configs;
- plan/subscription state.

### AGENT-1: agent versioning

Tasks:

- agent versions table;
- draft/test/publish workflow;
- rollback to previous version;
- prompt policy fields;
- model/provider config;
- evaluation before publish.

### RAG-1: production knowledge pipeline

Tasks:

- file upload to object storage;
- URL crawler with allowlist;
- PDF/docx/html parsers;
- chunking policies;
- embedding provider abstraction;
- Qdrant upsert/delete;
- reindex jobs;
- source freshness;
- unresolved topic recommendations.

Acceptance:

- indexed source is queryable;
- deleted source removes vectors;
- failed ingestion is retryable;
- source attribution always present.

### LLM-1: model gateway

Tasks:

- provider abstraction;
- prompt templates;
- safety filters;
- caching;
- timeout/retry;
- token/cost accounting;
- no-answer decision;
- model eval traces.

### ACTION-1: production Action Engine

Tasks:

- tool registry table;
- execution queue;
- retries/dead-letter;
- confirmation tokens;
- idempotency repository;
- output schema validation;
- audit log;
- provider error taxonomy.

### CHANNEL-1: real Telegram and widget

Tasks:

- Telegram webhook endpoint;
- message deduplication;
- outgoing message queue;
- web widget session API;
- CORS/domain allowlist;
- file/image handling later.

### VOICE-1: SIP/Asterisk voice

Tasks:

- ARI connection;
- call session lifecycle;
- streaming STT;
- TTS playback;
- interruption/barge-in;
- latency optimization;
- call recording and transcript policy.

### BILLING-1: subscription and usage

Tasks:

- plans;
- usage counters;
- invoices;
- YooKassa payments via redirect;
- webhooks;
- paid/past_due/suspended states;
- no card data storage.

### ANALYTICS-1: events and dashboards

Tasks:

- event schema;
- daily aggregates;
- automation rate;
- cost per resolution;
- CSAT;
- unresolved topics;
- sales conversions;
- export CSV.

## API quality rules

- typed Pydantic schemas for all endpoints;
- explicit error codes;
- idempotency key for mutations where replay is possible;
- pagination for lists;
- tenant_id always enforced server-side;
- OpenAPI examples;
- contract tests.
