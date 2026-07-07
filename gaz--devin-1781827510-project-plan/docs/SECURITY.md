# Security

## Current controls

- JWT access tokens with refresh sessions.
- Refresh rotation and logout revocation.
- MFA/TOTP foundation.
- RBAC roles and permissions.
- Tenant isolation checks.
- Audit logs.
- API key management.
- Webhook signature contracts.
- Integration secret encryption helpers.
- Rate limiting.
- Secure response headers middleware.
- Startup guard against default token secret in production.
- Runtime guardrails for opt-out intent, human handoff intent, regulated topics, unsafe outbound claims and unsafe tool calls.
- Per-tenant guardrail policy API/UI for prompt injection blocking, human handoff, regulated-topic escalation, toxicity escalation, outbound safety, tool safety, AI disclosure and custom regulated/prohibited phrases.
- Per-channel compliance policy API/UI for `autopilot`, `draft_only` and `human_approval`, plus outbound disable controls, opt-out notices, consent-required outbound controls and per-conversation auto-reply caps for messaging and voice.
- Durable contact suppression/do-not-call storage with API create/list/revoke and outbound blocking.
- Durable contact consent storage with API create/list/revoke, expiry support and consent-required outbound blocking for operator sends and voice calls.
- Bandit and Safety checks in local verification.

## Required production rules

- No default secrets in production.
- `ALLOW_LEGACY_TENANT_HEADER=false` in staging and production.
- `SEED_DEMO_DATA=false` in production.
- All public endpoints must have explicit rate limits.
- All webhooks must verify provider signatures or use approved test mode.
- All integration credentials must be encrypted at rest or stored in a secrets manager.
- Security scans must fail CI for high/critical issues. The workflow is configured as blocking; the remaining proof is a green GitHub Actions run.
- Production logs must not contain raw tokens, passwords, payment secrets or private customer data.

## Data protection

Current foundation:

- Tenant-scoped data model.
- Audit trail.
- Token/session security.
- Secret encryption helpers.

Needed before enterprise production:

- Data retention policy.
- Data export/delete flow.
- Call recording consent policy.
- Live-provider do-not-call, opt-out and outbound-consent enforcement proof.
- PII masking in logs and traces.
- Backup encryption and access policy.
- Threat model for voice, webhooks, billing and RAG.

## Security gaps

P0:

- Verify blocking security CI on GitHub Actions.
- Verify webhook signatures for live providers.
- Expand runtime guard rails beyond the initial policy engine with larger red-team datasets, provider-specific consent templates and live-provider compliance evidence.
- Prove opt-out/do-not-call/consent enforcement across all live providers.
- Run a documented threat model.

P1:

- Add retention/export/delete workflows.
- Add SSO/SAML/OIDC roadmap.
- Add secrets rotation runbook.
- Add audit review dashboard for suspicious activity.
