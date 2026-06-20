# 06. Frontend, UX/UI and design plan

## Frontend goal

The frontend must feel like a polished SaaS control center, not a technical demo.
It should help a non-technical owner launch an AI operator safely.

## Main product surfaces

### 1. Public website

Purpose: sell the product.

Pages:

- landing;
- pricing;
- industries: restaurants, clinics, e-commerce, services;
- integrations pages: Telegram, iiko, YooKassa, SIP/Asterisk;
- security/compliance;
- case studies;
- ROI calculator;
- book demo / start pilot.

### 2. Onboarding wizard

Flow:

1. create tenant;
2. choose industry;
3. connect channel;
4. upload knowledge;
5. configure agent persona;
6. run test questions;
7. review risk/no-answer cases;
8. publish sandbox;
9. invite operator;
10. go live.

### 3. Admin dashboard

Must show:

- automation rate;
- conversations handled;
- unresolved topics;
- saved hours;
- usage cost;
- provider readiness;
- incidents/quality warnings.

### 4. Agent builder

Sections:

- basic identity;
- tone/persona;
- allowed topics;
- forbidden topics;
- escalation rules;
- actions/tools;
- knowledge scope;
- test console;
- publish checklist.

### 5. Knowledge hub

Features:

- upload files;
- add URLs;
- add FAQ manually;
- connect integrations;
- ingestion status;
- coverage score;
- unresolved topic suggestions;
- source preview;
- reindex/delete.

### 6. Conversations and operator inbox

Features:

- live threads;
- AI/human transcript;
- sources used;
- actions called;
- confidence;
- handoff reason;
- operator reply;
- tags;
- status/resolution.

### 7. Analytics

Views:

- overview;
- automation;
- quality;
- cost;
- channels;
- unresolved topics;
- agent versions comparison.

## Design principles

- trust first: show why AI answered;
- business language, not ML jargon;
- every risky action has preview/confirmation;
- empty states teach next action;
- demo data should look like real restaurant/service operations;
- mobile-friendly operator inbox;
- accessibility: keyboard navigation, contrast, labels.

## Visual system

Suggested direction:

- clean B2B SaaS;
- dark text, light cards, high contrast;
- accent color for AI/automation;
- status colors: green ready, amber needs attention, red blocked;
- compact tables for operators;
- clear stepper for onboarding.

Core components:

- `DashboardShell`;
- `StatusPill`;
- metric cards;
- integration cards;
- checklist rows;
- conversation timeline;
- source citation card;
- action audit card;
- empty state;
- loading/error/fallback banners.

## Frontend technical plan

- keep server-side API client for secure data loading;
- add typed mutations via server actions/API routes;
- add auth/session handling;
- add form validation with shared schemas;
- add optimistic UI for low-risk updates;
- add Storybook or component preview;
- add Playwright E2E for golden flows;
- add visual regression for core pages.

## UX acceptance criteria

A new user should be able to:

- understand value in 10 seconds on landing;
- start a pilot request in < 1 minute;
- create first agent in < 10 minutes;
- upload knowledge and see indexing status;
- test 10 questions and understand failures;
- publish sandbox only after checklist passes;
- see ROI after first conversations.
