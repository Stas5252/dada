# 15. Final gaps and risk register

## Purpose

This document lists everything that must be resolved before selling to real paying customers. Each item is a risk or gap that could block revenue or damage reputation.

---

## Risk register

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|------------|------------|
| 1 | AI hallucination in critical domain (medical, legal) | Critical — reputation, legal liability | Medium | No-answer policy, source-only answers, guardrails, human handoff, eval tests |
| 2 | Personal data breach (152-ФЗ violation) | Critical — fines up to 18M ₽, business closure | Medium | Data in RF, encryption, access control, DPA, privacy policy, Roskomnadzor analysis |
| 3 | LLM provider outage/degradation | High — customers get no answers | Medium | Multi-provider fallback, graceful degradation message, queue + retry |
| 4 | Unit economics negative at scale | High — unsustainable business | Medium | Cost tracking per tenant, usage caps, tier pricing, caching, model optimization |
| 5 | First pilot fails publicly | High — kills referrals | Low-Medium | Controlled scope, readiness gates, daily review, kill switch, NDA pilot |
| 6 | Competitor copies positioning | Medium — price pressure | High | Speed to market, RF compliance moat, integration depth, presets, customer success |
| 7 | No product-market fit | Critical — no revenue | Medium | Validate with 3-5 manual pilots before heavy investment |
| 8 | Key person dependency (solo founder) | High — project stalls | High | Document everything, automate, use AI assistants, plan hiring |
| 9 | Payment integration failure (YooKassa) | Medium — can't bill | Low | Sandbox testing, webhook idempotency, manual invoice fallback |
| 10 | Voice quality too low for production | Medium — channel unusable | Medium | Start with chat only, add voice after chat proven, latency optimization |
| 11 | Customer churn after pilot | High — no recurring revenue | Medium | Success metrics, weekly tuning, ROI reports, long-term value |
| 12 | Legal entity not ready | Medium — can't sign contracts | Low | Register ИП/ООО before first paid pilot |
| 13 | Domain/brand conflict | Low — rename cost | Low | Check ФИПС before investing in brand |
| 14 | Prompt injection attack | Medium — wrong actions executed | Medium | Input sanitization, tool permissions, confirmation tokens, audit |
| 15 | Scaling bottleneck (DB/vector/infra) | Medium — performance degradation | Low early | Load testing before scale phase, horizontal scaling plan |

---

## Pre-production checklist (legal/business)

### Legal entity

- [ ] Register ИП or ООО.
- [ ] Open bank account.
- [ ] Choose tax regime (УСН 6% or 15%).
- [ ] Register as personal data operator (if needed by scale).
- [ ] Prepare standard contract/оферта.
- [ ] Prepare DPA (договор обработки ПДн).
- [ ] Prepare privacy policy for end users.
- [ ] Check trademark availability (ФИПС search).
- [ ] Register domain.

### Financial operations

- [ ] Accounting: self or outsourced бухгалтер.
- [ ] Invoicing process.
- [ ] Act of work / закрывающие документы.
- [ ] Tax calendar.
- [ ] Revenue recognition rules.

### Insurance / liability

- [ ] Disclaimer: AI is not a replacement for professional advice.
- [ ] Limitation of liability in contract.
- [ ] No guarantees of specific automation rate.
- [ ] Force majeure clause.

---

## Pre-production checklist (technical)

### Infrastructure

- [ ] Production PostgreSQL in RF datacenter.
- [ ] Production Qdrant in RF.
- [ ] Object storage (S3-compatible) in RF.
- [ ] Redis for queues/cache.
- [ ] HTTPS with valid certificate.
- [ ] DNS and domain.
- [ ] Backups automated and tested.
- [ ] Monitoring and alerting.
- [ ] Log aggregation.
- [ ] Secret manager (not .env in production).

### Security

- [ ] Penetration test or self-audit.
- [ ] RBAC tested per tenant.
- [ ] Rate limiting on all public endpoints.
- [ ] Input validation everywhere.
- [ ] Output sanitization.
- [ ] No secrets in logs.
- [ ] PII masking in logs/traces.
- [ ] Dependency vulnerability scanning.
- [ ] Incident response plan.

### AI safety

- [ ] Golden question evaluation suite (50+ questions per vertical).
- [ ] Hallucination detection in eval.
- [ ] No-answer threshold tuned.
- [ ] Prompt injection test suite.
- [ ] Human handoff tested end-to-end.
- [ ] Source attribution verified.
- [ ] Forbidden topic list configured.
- [ ] Confidence threshold calibrated.

### Deployment

- [ ] CI/CD pipeline.
- [ ] Staging environment.
- [ ] Blue-green or rolling deploy.
- [ ] Database migration strategy.
- [ ] Rollback tested.
- [ ] Smoke tests post-deploy.
- [ ] Feature flags for risky features.

---

## Pre-production checklist (product)

### Core flows verified

- [ ] Tenant registration and onboarding.
- [ ] Knowledge upload and indexing.
- [ ] Agent creation and testing.
- [ ] Channel connection (Telegram minimum).
- [ ] Real conversation with source-grounded answer.
- [ ] No-answer → handoff flow.
- [ ] Operator sees full context.
- [ ] Analytics dashboard shows real data.
- [ ] Billing tracks usage.

### Demo readiness

- [ ] Demo tenant with realistic data.
- [ ] Demo script documented.
- [ ] Sales can run demo independently.
- [ ] Landing page live.
- [ ] ROI calculator works.
- [ ] One-pager PDF available.
- [ ] Presentation deck ready.

---

## Pre-production checklist (customer success)

- [ ] Onboarding questionnaire ready.
- [ ] Pilot setup checklist.
- [ ] Daily/weekly review process.
- [ ] Pilot report template.
- [ ] Escalation contacts for customer.
- [ ] Knowledge tuning process documented.
- [ ] Handoff operator training materials.
- [ ] Success metrics defined per customer.

---

## Brand and marketing gaps

- [ ] Company name finalized.
- [ ] Domain purchased.
- [ ] Logo designed.
- [ ] Brand guidelines basic.
- [ ] Social profiles created.
- [ ] Telegram channel/bot for updates.
- [ ] Email for business communication.
- [ ] Case study template.
- [ ] Testimonial collection process.

---

## Anti-abuse and safety

- [ ] Rate limiting per user/tenant.
- [ ] Spam detection.
- [ ] Toxic message handling.
- [ ] Block/ban capability.
- [ ] Usage alerts for abnormal volume.
- [ ] Cost caps per tenant.
- [ ] Prompt injection detection.
- [ ] Tool execution confirmation for destructive actions.
- [ ] Audit trail for all AI decisions.

---

## Enterprise readiness (later, after first revenue)

- [ ] SSO/SAML.
- [ ] Custom SLA.
- [ ] Security questionnaire answers.
- [ ] SOC 2 or equivalent (long-term).
- [ ] Private deployment documentation.
- [ ] Multi-region support.
- [ ] Custom integration SLA.
- [ ] Dedicated account manager process.

---

## Decision log (to fill as project progresses)

| Date | Decision | Rationale | Owner |
|------|----------|-----------|-------|
| — | Start with restaurants as first vertical | High volume, clear ROI, structured data | Founder |
| — | API LLM first, local later | Faster launch, better quality initially | Founder |
| — | Telegram + web widget as first channels | Most common for RF SMB | Founder |
| — | ИП for start, ООО when revenue > threshold | Lower admin burden initially | Founder |

---

## Summary

Before first paid customer:

1. Legal entity exists.
2. Contract/оферта signed.
3. Privacy policy published.
4. Production infra in RF.
5. One vertical preset works end-to-end.
6. Golden questions pass evaluation.
7. Handoff flow tested.
8. Dashboard shows real metrics.
9. Billing works (at least manual invoice).
10. Incident response plan exists.
