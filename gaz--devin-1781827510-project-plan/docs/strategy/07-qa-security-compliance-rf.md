# 07. QA, security and Russian compliance plan

> This document is an engineering/product checklist, not legal advice. Before production launch, validate policies and contracts with a qualified Russian legal/privacy specialist.

## QA strategy

### Test pyramid

1. Unit tests
   - schema validation;
   - RAG chunking/retrieval;
   - RBAC;
   - idempotency;
   - provider adapters;
   - billing calculations.
2. Integration tests
   - PostgreSQL repository;
   - Qdrant indexing;
   - Redis queues;
   - provider sandbox APIs;
   - webhook signatures.
3. Contract tests
   - OpenAPI;
   - JSON schemas;
   - tool input/output;
   - frontend/backend types.
4. E2E tests
   - register → connect channel → upload knowledge → test chat → publish;
   - Telegram message → AI answer → handoff;
   - payment creation → webhook → invoice state;
   - voice call lifecycle.
5. AI evaluation tests
   - golden question set;
   - hallucination checks;
   - no-answer correctness;
   - source attribution;
   - regression by agent version.

### Release gates

Every release must pass:

- lint;
- typecheck;
- backend tests;
- frontend build;
- npm audit;
- pre-commit;
- DB migration dry-run;
- smoke test on staging;
- AI eval for affected agent/RAG changes.

## Security baseline

### Application security

- JWT/refresh tokens;
- RBAC for all admin APIs;
- tenant isolation tests;
- rate limits;
- input validation;
- output sanitization;
- CSRF/CORS rules;
- audit logs;
- secret manager;
- dependency scanning;
- SAST later.

### Data security

- encryption at rest where provider supports it;
- TLS everywhere;
- no secrets in logs;
- PII masking;
- retention policy per tenant;
- backups encrypted;
- access logs for admins;
- data export/delete procedures.

### AI safety

- no-answer policy;
- source-required answers;
- prompt injection detection for knowledge sources;
- tool permissions;
- destructive action confirmation;
- model output validation;
- human handoff for low confidence;
- conversation audit trail.

## Russian legal/compliance checklist

### 152-ФЗ Personal Data

Key requirements to plan for:

- identify whether company is personal data operator;
- define purposes and legal bases for processing;
- collect consent where required;
- publish personal data processing policy;
- notify Roskomnadzor before processing where required by Art. 22 exceptions analysis;
- maintain data subject rights process;
- appoint responsible person/process;
- implement organizational and technical measures.

### 242-ФЗ localization

For Russian citizens' personal data, initial recording, systematization, accumulation, storage, update/change and extraction must be performed using databases located in Russia, unless a legal exception applies.

Product implication:

- production DB and object storage for Russian customers should be in RF region;
- external AI/model providers must be assessed carefully;
- if foreign processors are used, cross-border transfer analysis is required;
- offer RF-hosted/private deployment option.

### Information security measures

Plan around:

- threat model for ИСПДн;
- level/category assessment;
- organizational measures;
- technical measures aligned with FSTEC Order No. 21 where applicable;
- access control;
- incident handling;
- vulnerability management;
- backups and recovery.

### Payments / YooKassa

Rules:

- prefer redirect/hosted payment page;
- do not store/process card data in Gaz platform;
- if collecting card data directly, PCI DSS scope appears — avoid this for early product;
- store only payment IDs/statuses/amounts;
- verify YooKassa webhooks with idempotency.

### Advertising and communications

If product sends marketing messages:

- separate service/support notifications from advertising;
- keep consent for marketing messages;
- unsubscribe mechanism;
- respect channel platform policies.

### Voice calls

Plan:

- disclosure/consent for call recording where required;
- retention for recordings/transcripts;
- PII masking in transcripts;
- access control for recordings;
- lawful purpose for processing.

## Compliance documents to prepare

- Privacy policy;
- Personal data processing policy;
- Consent text;
- Cookie policy if web tracking is used;
- DPA / data processing agreement;
- Information security policy;
- Incident response policy;
- Retention/deletion policy;
- Subprocessor list;
- Security questionnaire;
- Terms of service;
- SLA/support terms.
