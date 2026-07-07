# Competitor benchmark (2026-07-03)

Goal: define the real bar for making CallForce competitive with Bland.ai and stronger for Russian-speaking SMB/enterprise workflows.

Primary official sources reviewed:

- Bland: https://www.bland.ai/, https://docs.bland.ai/welcome-to-bland, https://docs.bland.ai/tutorials/testbed, https://docs.bland.ai/tutorials/warm-transfer, https://docs.bland.ai/enterprise-features/SIP-integration
- Retell AI: https://docs.retellai.com/general/introduction, https://docs.retellai.com/test/test-overview
- Vapi: https://docs.vapi.ai/quickstart/introduction, https://docs.vapi.ai/quickstart
- PolyAI: https://poly.ai/
- Intercom Fin: https://www.intercom.com/help/en/articles/7120684-fin-ai-agent-explained, https://www.intercom.com/pricing
- Zendesk AI Agents: https://support.zendesk.com/hc/en-us/articles/6970583409690-About-AI-agents, https://www.zendesk.com/service/ai/
- Ada: https://www.ada.cx/, https://www.ada.cx/platform/

## Summary table

| Product | Strong side | Weak side / opportunity for CallForce | CallForce response |
| --- | --- | --- | --- |
| Bland.ai | Voice AI, SIP, Testbed, warm transfer, enterprise voice workflows | Less tailored to RF/SNG integrations and local business operations | Match voice quality/testbed, beat with Telegram/VK/iiko/YooKassa/RF workflows |
| Retell AI | Build/test/deploy/monitor voice agents, inbound/outbound phone agents | Primarily voice-agent platform, less full SMB operating suite | Keep voice parity, add omnichannel inbox, billing, CRM/order workflows |
| Vapi | Developer-first voice AI infrastructure, swappable transcriber/model/voice pipeline | More developer platform than ready SMB SaaS cockpit | Keep provider abstraction, add no-code setup and vertical templates |
| PolyAI | Enterprise voice agents, dialog platform, high-call-volume CX positioning | Enterprise sales motion, less SMB self-serve | Offer faster self-serve launch for local businesses |
| Intercom Fin | Mature helpdesk, omnichannel support, outcome pricing, inbox handoff | Support-first, not voice-first for local calls/sales | Combine inbox quality with voice/calls, iiko/CRM and lead recovery |
| Zendesk AI Agents | Mature service suite, messaging/email/web/voice EAP, actions and reporting | Heavier enterprise stack, can feel complex | Simpler onboarding, local integrations and tighter AI agent builder |
| Ada | Omnichannel customer service AI, enterprise CX optimization | Support automation focus, not local sales/calls first | Emphasize sales, calls, bookings, missed leads and revenue reports |

## Must-have features

- Inbound and outbound calls.
- SIP/Twilio/Asterisk provider abstraction.
- Low-latency streaming STT/LLM/TTS.
- Barge-in, silence detection, call transfer and fallback.
- Testbed with scenario suites, thresholds and publish gates.
- Guard rails for prohibited claims, opt-out, escalation and unsafe tool calls.
- Omnichannel inbox: web widget, Telegram, VK, WhatsApp, email, generic webhook.
- Agent builder with templates for salons, clinics, restaurants, delivery, auto service, B2B sales and e-commerce.
- Knowledge/RAG with file and URL ingestion, citations, no-answer policy and quality eval.
- CRM/order/payment actions with idempotency and audit.
- Human handoff and operator console.
- Usage billing, plans, limits and payment webhooks.
- Analytics: automation rate, conversion, missed leads, cost savings, quality, call outcomes.
- Security: RBAC, MFA, audit, encrypted integration secrets, tenant isolation.

## Killer features for CallForce

1. One inbox for AI and human work across chat, messengers, social and voice.
2. AI can call and write according to explicit business rules, not just answer.
3. AI creates and updates leads/orders in CRM/iiko/YooKassa-style local workflows.
4. Missed lead recovery: calls/messages/follow-ups from one campaign cockpit.
5. Lost-money analytics: show where the business loses calls, leads and orders.
6. AI supervisor: quality checks, risky claims, objection handling and weekly growth report.
7. Draft/approval/autopilot modes per channel.
8. Russian-first templates, channels and compliance posture.
9. Bland-style Testbed plus RAG eval before publish.
10. Local/self-host path for privacy-sensitive customers.

## Target positioning

CallForce should not position itself as a generic chatbot. The product category should be:

AI Omnichannel Sales & Support Platform for calls, messengers, lead recovery and local business operations.

The strongest wedge is not "we have AI voice too". The strongest wedge is:

- voice plus messaging;
- Russian/local channels;
- vertical business templates;
- operator handoff;
- CRM/order/payment actions;
- measurable recovered revenue.
