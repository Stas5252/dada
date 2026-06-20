# 01. Market benchmark: как сделать не хуже Intercom/Zendesk/Ada/Sierra, а лучше для РФ

## Кого считаем эталоном

Ориентиры по рынку AI customer support:

- **Intercom Fin** — сильный AI agent, knowledge grounding, procedures/tools, handoff, reporting.
- **Zendesk AI Agents** — enterprise suite, omnichannel, actions/API integrations, analytics, human-agent workflows.
- **Ada** — no-code automation builder, multilingual support, controlled bot flows.
- **Sierra / Decagon** — agent-first enterprise automation, voice + chat, strong guardrails, complex workflows.
- **Freshdesk/Freddy, Salesforce Agentforce** — SMB/CRM distribution and enterprise integrations.

## Что у лидеров рынка обязательно есть

| Capability | Что это значит для нас |
| --- | --- |
| Grounded AI answers | Ответ только по trusted knowledge, source attribution, no-answer policy. |
| Procedures / workflows | Не только чат, а сценарии: собрать данные, вызвать tool, уточнить, эскалировать. |
| Authorized actions | Заказ, платеж, статус, отмена, webhooks — с permissions, idempotency, audit. |
| Human handoff | Правильная передача оператору с transcript, reason, priority, context. |
| Omnichannel | Telegram, web widget, email/API, voice/SIP, позже WhatsApp/VK при юридической возможности. |
| Analytics | automation rate, containment, CSAT, deflection, unresolved topics, cost per resolution. |
| Admin UX | Бизнес-пользователь без программиста настраивает агента, знания и правила. |
| Enterprise trust | Security, audit, RBAC, SSO, data retention, compliance, SLA. |

## Где можно быть лучше для российского рынка

1. **Российские интеграции из коробки**
   - iiko/R-Keeper, ЮKassa/CloudPayments, Telegram, amoCRM/Битрикс24, SIP/Asterisk, МойСклад.
2. **152-ФЗ-ready deployment**
   - хранение первичных данных граждан РФ в РФ;
   - понятные документы для оператора ПДн;
   - локальный/частный контур для клиентов с повышенными требованиями.
3. **Русский язык и локальные сценарии**
   - тон общения, морфология, адреса, телефоны, российские платежи, доставка, часовые пояса.
4. **Быстрый ROI для SMB**
   - не “enterprise transformation”, а запуск за 1–3 дня: Telegram + база знаний + платеж/заказ.
5. **Hybrid AI + human ops**
   - продукт должен помогать продавать не только SaaS, но и услугу внедрения/ведения базы знаний.

## North Star

**Customer automation revenue:** сколько денег клиент сэкономил/заработал благодаря платформе.

Внутренние метрики:

- automation rate / containment: 60% MVP, 75% v1, 85% ideal;
- p95 response latency chat < 2s, voice turn latency < 1.2s после STT;
- answer accuracy on golden set > 92%;
- hallucination/unsupported answer < 1%;
- handoff context completeness > 95%;
- first setup time < 30 минут для demo tenant;
- first production launch < 3 дня для SMB.

## Product moat

- Российские интеграции + compliance pack.
- Agent workflow builder, который понятен владельцу бизнеса.
- RAG quality loop: unresolved topics автоматически превращаются в рекомендации по базе знаний.
- Voice + chat в одном агенте и одной аналитике.
- Transparent audit: почему агент ответил/вызвал tool/передал оператору.
