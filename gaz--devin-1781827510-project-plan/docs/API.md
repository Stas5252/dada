# API overview

Base path:

```text
/api/v1
```

## Auth and account

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/login/mfa`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/mfa/setup`
- `POST /auth/mfa/verify`
- `POST /auth/mfa/recovery-codes`
- `POST /auth/mfa/disable`
- `POST /auth/verify-email`
- `POST /auth/request-password-reset`
- `POST /auth/reset-password`

## Tenant/workspace

- `GET /tenants/{tenant_id}/dashboard`
- `GET /tenants/{tenant_id}/settings`
- `POST /tenants/{tenant_id}/settings`
- `GET /tenants/{tenant_id}/settings/integration-readiness`
- `GET /tenants/{tenant_id}/settings/channel-webhooks`
- `GET /tenants/{tenant_id}/settings/guardrails`
- `POST /tenants/{tenant_id}/settings/guardrails`
- `GET /tenants/{tenant_id}/settings/channel-policies`
- `POST /tenants/{tenant_id}/settings/channel-policies`
- Team routes in `api/v1/team.py`
- Audit routes in `api/v1/audit.py`
- API key routes in `api/v1/api_keys.py`

Guardrail settings contract:

- `enabled`, `opt_out_enabled`, `human_handoff_enabled`, `regulated_topics_enabled`, `prompt_injection_block_enabled`, `toxicity_escalation_enabled`, `outbound_safety_enabled`, `tool_safety_enabled`, `ai_disclosure_required`.
- `custom_regulated_terms` and `custom_prohibited_claims` accept up to 50 normalized phrases each.
- Tenant settings are merged on update, so channel credentials and guardrail policy do not erase each other.

Channel policy settings contract:

- `mode`: `autopilot`, `draft_only` or `human_approval`.
- `outbound_enabled`: blocks operator sends/outbound calls when disabled.
- `ai_disclosure_required`: injects AI disclosure rules into the channel prompt.
- `require_opt_out_notice`: appends the standard opt-out notice to allowed automated messaging replies.
- `require_contact_consent_for_outbound`: blocks operator sends/outbound calls unless an active contact consent record exists.
- `max_auto_replies_per_conversation`: blocks further automated replies in a conversation and escalates it when the per-channel limit is reached.
- Supported policy sections: `default_policy`, `web_widget`, `telegram`, `vk`, `whatsapp`, `voice`.

Integration readiness contract:

- `status`: `ready`, `mock_mode` or `action_required`.
- `items`: tenant-scoped checklist entries for LLM, speech, web widget, Telegram, VK, WhatsApp, Twilio, SIP/Asterisk, YooKassa and iiko.
- Each item returns `configured_settings` and `missing_settings` names only. Secret values are never returned.
- `blocking=true` means the item blocks a real production launch for that tenant until configured.

Channel webhook diagnostics contract:

- `public_url_status`: `https_ready`, `local_only` or `missing`.
- `items`: tenant-scoped diagnostics for Telegram, VK and WhatsApp webhooks.
- Each item returns callback URL, setup status, missing setting names, warnings and security notes.
- Secret values such as bot tokens, VK secret keys, WhatsApp verify tokens and app secrets are never returned.
- WhatsApp live inbound callbacks require `whatsapp_app_secret`; VK should use `vk_secret_key`.

## Agents and Testbed

- Agent routes in `api/v1/agents.py`
- Pathway support and scenario validation.
- Testbed routes in `api/v1/testbed.py`.
- `GET /agents/{agent_id}/testbed/readiness` returns publish readiness, required pass rate, pass/fail/running/stale/missing counts, latest run summaries and blocking failures.

Agent profile contract:

- Create/update accepts `business_profile`, `agent_role`, `agent_tone`, `agent_language`, `business_hours`, `escalation_rules`, `sales_rules`, `forbidden_topics` and `enabled_tools`.
- `forbidden_topics` can be posted as a string list, newline text or comma-separated text; API stores a normalized unique list.
- `enabled_tools` is normalized against the backend tool registry and always includes `escalate_to_human`.
- Current native tools: `escalate_to_human`, `add_to_cart`, `remove_from_cart`, `checkout_cart`, `confirm_order`.
- Order/cart context and order-specific prompt rules are included only when order tools are enabled for that agent.
- Profile, prompt, channel and enabled-tool changes return a published agent to `draft` so Testbed can re-approve the new runtime behavior.

Publish contract:

- `POST /agents/{agent_id}/publish` returns `409 TESTBED_PUBLISH_GATE_FAILED` when the agent has no Testbed cases, a case has no run, the latest run is `running`/`failed`, or the latest passed run is stale after an agent/scenario update.
- A successful publish requires at least one Testbed case and a `100%` pass rate across current cases using latest non-stale `passed` runs.
- Publish-block responses include `pass_rate`, `required_pass_rate`, `total_cases` and per-case failure details.

Remaining production gap: add larger scenario suites, per-node assertions and CI quality checks from stored Testbed results.

## Knowledge/RAG

- Knowledge routes in `api/v1/knowledge.py`.
- Supports source management, upload, ingestion jobs and Qdrant contract.
- `POST /knowledge/eval` runs tenant-scoped golden RAG checks for expected source titles, expected answer terms, citation presence and no-answer behavior. It returns pass rate, required pass rate and per-case failures. The knowledge page exposes the same check as a RAG quality eval panel.
- Parsers cover common document/web inputs.

Production gap: expand golden datasets, connect eval thresholds to CI and add quality trend history.

## Conversations and channels

- Conversation routes in `api/v1/conversations.py`.
- Contact suppression routes:
  - `GET /contact-suppressions`
  - `POST /contact-suppressions`
  - `DELETE /contact-suppressions/{suppression_id}`
- Contact consent routes:
  - `GET /contact-consents`
  - `POST /contact-consents`
  - `DELETE /contact-consents/{consent_id}`
- Widget route in `api/v1/widget.py`.
- Telegram route in `api/v1/telegram.py`.
- VK route in `api/v1/vk.py`.
- WhatsApp route in `api/v1/whatsapp.py`.
- Generic/custom integrations in `api/v1/integrations.py`.

Runtime safety: opt-out guardrails persist contact suppressions and block later outbound calls/operator sends for suppressed contacts. Contact consents are durable, can expire, can be revoked and are enforced when `require_contact_consent_for_outbound` is enabled for a channel. Per-tenant guardrail policy controls prompt injection blocking, human handoff, regulated-topic escalation, toxicity escalation, outbound claim blocking, tool-call safety and AI disclosure prompting. Per-channel automation policy controls whether web widget, Telegram, VK and WhatsApp replies are sent immediately or stored as drafts for operator approval, enforces per-conversation auto-reply limits, can append an opt-out notice to automated messaging replies and can require active consent before outbound operator messages or voice calls.

Production gap: verify real provider webhooks, live-provider opt-out/consent behavior and UI setup wizards.

## Voice

- Voice routes in `api/v1/voice.py`.
- Twilio service in `app/twilio_service.py`.
- Asterisk ARI service in `app/asterisk_ari_service.py`.
- Speech services in `app/speech_service.py`.

Production gap: real call, streaming STT/TTS, latency, recording and transfer proof.

## Billing

- Billing routes in `api/v1/billing.py`.
- `GET /billing/status` returns `plan`, monthly `messages_used`, `messages_limit`, `messages_remaining`, `billing_period_start`, `limit_exceeded` and `conversations_used`.
- AI-turn entrypoints call billing enforcement before creating new messages. When the tenant is over the monthly message limit they return `402 BILLING_LIMIT_REACHED` and write a `billing.limit_blocked` audit event.
- Tenant setting `billing_monthly_message_limit` can override the plan default for pilots, manual contracts and enterprise exceptions.
- Ledger and YooKassa provider foundation.

Production gap: subscriptions, limits, webhooks and reconciliation must be verified in sandbox.

## Health

- `GET /health`
- `GET /readiness`

Use `/api/v1/health` for local smoke checks.
