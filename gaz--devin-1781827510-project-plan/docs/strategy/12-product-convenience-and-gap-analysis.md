# 12. Product convenience and gap analysis: what else to account for

## Goal

Make the platform convenient enough that customers can launch without constant developer help, while still supporting expert implementation when needed.

## What must be convenient

### First launch

- industry preset selection;
- demo data generation;
- guided checklist;
- inline examples;
- progress indicator;
- “test before publish” flow;
- publish blocked until readiness passes.

### Knowledge management

- drag-and-drop file upload;
- URL import;
- manual FAQ editor;
- duplicate detection;
- outdated source warnings;
- unresolved topic suggestions;
- source quality score;
- reindex button;
- preview chunks and citations.

### Agent setup

- persona templates;
- tone examples;
- forbidden topics;
- escalation rules;
- answer examples;
- test console;
- version history;
- rollback.

### Integrations

- connection wizard;
- sandbox/test mode;
- health checks;
- last sync status;
- retry failed webhook;
- permission explanation;
- safe credential handling.

### Operator experience

- inbox with filters;
- handoff reason;
- summary;
- AI actions history;
- suggested reply;
- customer profile;
- internal notes;
- close/reopen conversation.

### Owner experience

- simple ROI dashboard;
- daily/weekly report;
- top unresolved questions;
- saved hours;
- missed leads recovered;
- channel performance;
- billing usage.

## Areas not fully covered yet

### Legal/product docs

- privacy policy;
- offer/terms;
- consent forms;
- DPA;
- SLA;
- support policy;
- subprocessor list;
- security page.

### Financial operations

- unit economics model;
- LLM cost calculator;
- telephony cost calculator;
- billing reconciliation;
- refunds;
- taxes/accounting handoff;
- pricing experiments.

### Implementation operations

- onboarding questionnaire;
- customer data import checklist;
- launch checklist;
- pilot report template;
- customer success scripts;
- support escalation process.

### Reliability edge cases

- provider outage fallback;
- LLM timeout fallback;
- Qdrant unavailable;
- duplicate webhooks;
- Telegram rate limits;
- voice call dropped;
- payment webhook delayed;
- database migration rollback;
- backup restore.

### AI quality edge cases

- conflicting knowledge sources;
- stale menu/prices;
- prompt injection in uploaded docs;
- angry customers;
- legal/medical/safety requests;
- competitor questions;
- profanity;
- multilingual messages;
- ambiguous customer intent.

### Data governance

- per-tenant retention;
- data export;
- data deletion;
- transcript anonymization;
- call recording policy;
- admin access review;
- audit export.

### Team/admin features

- invite users;
- roles;
- operator groups;
- business hours;
- SLA rules;
- notification preferences;
- approval workflow for publishing.

### Marketplace/future

- integration marketplace;
- partner portal;
- white-label mode;
- templates marketplace;
- agency account managing multiple clients.

## Ideal product backlog by priority

### P0 before first paid pilot

- real Telegram webhook;
- web widget;
- production PostgreSQL/Qdrant;
- knowledge upload;
- test console;
- operator handoff;
- basic analytics;
- pilot report;
- landing page;
- security/privacy basics.

### P1 before broader launch

- presets;
- onboarding wizard;
- iiko integration;
- YooKassa redirect;
- billing plans;
- staging/prod deploy;
- E2E tests;
- monitoring;
- compliance docs.

### P2 to become market leader

- voice/SIP;
- advanced workflow builder;
- evaluation lab;
- unresolved topic auto-suggestions;
- partner portal;
- enterprise SSO;
- private deployment;
- marketplace.

## “Done right” checks

Every new feature must answer:

- Does it reduce launch time?
- Does it improve customer ROI?
- Does it reduce risk of wrong AI answer?
- Does it create reusable preset/template value?
- Does it have tests?
- Does it have docs/runbook?
- Does it expose success metrics?
