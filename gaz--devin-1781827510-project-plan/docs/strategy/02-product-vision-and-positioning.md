# 02. Product vision and positioning

## Одно предложение

Gaz AI Support Platform — российская AI-платформа, которая берет на себя первую линию поддержки и продаж в Telegram, на сайте и по телефону, отвечает по базе знаний, выполняет действия в iiko/CRM/платежах и передает сложные кейсы оператору с полным контекстом.

## Для кого продукт

### ICP-1: рестораны и доставка

Pain:

- много одинаковых вопросов: меню, доставка, статус заказа, бронь, оплата;
- операторы перегружены;
- клиенты уходят, если долго отвечают;
- iiko/Telegram/телефония живут отдельно.

Value:

- Telegram + виджет + voice agent;
- ответы по меню/FAQ;
- статус заказа и создание заказа через iiko;
- оплата через ЮKassa;
- handoff оператору.

### ICP-2: сервисные компании и клиники

Pain:

- запись, перенос, FAQ, подготовка к визиту;
- звонки после рабочего времени;
- нужно не терять лиды.

Value:

- AI frontdesk;
- запись/квалификация лида;
- reminders;
- operator handoff.

### ICP-3: e-commerce и локальные бренды

Pain:

- статусы заказов, возвраты, доставка, наличие;
- большой support backlog;
- высокая стоимость операторов.

Value:

- order status automation;
- return/exchange procedures;
- knowledge recommendations;
- analytics по unresolved topics.

## Позиционирование

Не “чатбот”. Не “просто GPT на сайте”.

**Правильно:** AI-оператор первой линии, который работает по вашим правилам, знает вашу базу знаний, умеет выполнять действия и безопасно передает человека оператору.

## Основные модули продукта

1. **AI Agent Builder**
   - persona, tone, guardrails, escalation policy;
   - versioning, draft/test/publish;
   - procedures/actions.
2. **Knowledge Hub**
   - файлы, URL, FAQ, интеграции;
   - ingestion, chunking, embeddings;
   - качество покрытия и unresolved topics.
3. **Omnichannel Inbox**
   - Telegram, web widget, SIP/voice;
   - единая история клиента;
   - handoff и операторские заметки.
4. **Action Engine**
   - iiko, платежи, CRM, webhooks;
   - idempotency, confirmation, RBAC, audit.
5. **Analytics & ROI**
   - automation rate;
   - saved operator hours;
   - revenue from assisted orders;
   - cost per resolution;
   - quality/hallucination reports.
6. **Compliance & Trust Center**
   - ПДн, логи, retention, DPA, security docs;
   - audit exports;
   - регион хранения данных.

## Продуктовые уровни

### MVP+ сейчас

- локальный Core API;
- mock/live frontend;
- auth, tenants, agents, knowledge, chat;
- local production service adapters;
- readiness dashboard.

### v1 paid pilot

- real Telegram bot;
- real web widget;
- production PostgreSQL/Qdrant;
- hosted deployment;
- basic billing;
- admin onboarding;
- operator handoff.

### v2 market-ready

- voice/SIP;
- iiko/ЮKassa production;
- analytics/ROI;
- workflow builder;
- compliance pack;
- customer success playbooks.

### v3 category leader

- multi-agent orchestration;
- voice quality near human;
- marketplace integrations;
- advanced evaluation lab;
- enterprise SSO/SAML;
- on-prem/private cloud option.
