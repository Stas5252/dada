# ARCHITECTURE.md — CallForce Platform

## Обзор

CallForce — AI-платформа omnichannel поддержки и продаж. Позволяет компаниям развернуть AI-агента, который общается с клиентами через голос, мессенджеры и web-виджет; ведёт CRM; обрабатывает заказы; проводит outbound-кампании.

## Стек технологий

| Слой | Технология |
|---|---|
| Backend API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 |
| База данных | PostgreSQL (prod), SQLite (local/test) |
| Векторная БД | Qdrant (`:memory:` для local, внешний URL для prod) |
| Очередь задач | Arq + Redis |
| LLM | OpenAI GPT-4o / GPT-4o-mini, vLLM (self-hosted Qwen), Yandex GPT |
| STT/TTS | Yandex SpeechKit (RU-first), Deepgram, OpenAI Whisper |
| Телефония | Twilio, Asterisk ARI/SIP |
| Мессенджеры | Telegram Bot API, VK Bot API, WhatsApp Cloud API |
| Платежи | YooKassa |
| CRM/Orders | iikoCloud |
| Frontend | Next.js 14, TypeScript, TailwindCSS |
| Мониторинг | Sentry, OpenTelemetry, Prometheus-compatible метрики |

## Архитектура

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                │
│   Dashboard · Agent Builder · Inbox · CRM · Voice   │
└──────────────────────┬──────────────────────────────┘
                       │ REST / WebSocket
┌──────────────────────▼──────────────────────────────┐
│                  FastAPI Backend                     │
│                                                      │
│  ┌──────────┐ ┌───────────┐ ┌─────────────────────┐ │
│  │ Auth/RBAC│ │Orchestrator│ │ Guard Rails (safety)│ │
│  └──────────┘ └─────┬─────┘ └─────────────────────┘ │
│                     │                                │
│  ┌──────────────────▼───────────────────────────────┐│
│  │              LLM Router (multi-model)            ││
│  │  OpenAI · vLLM · fallback chain                  ││
│  └──────────────────────────────────────────────────┘│
│                                                      │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐            │
│  │   RAG    │ │   Voice   │ │  Channels│            │
│  │ (Qdrant) │ │ STT + TTS │ │ TG/VK/WA │            │
│  └──────────┘ └───────────┘ └──────────┘            │
│                                                      │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐            │
│  │   CRM    │ │  Billing  │ │  Outbound│            │
│  │ Leads/   │ │ YooKassa  │ │ Campaigns│            │
│  │ Deals    │ │ Usage     │ │ Follow-up│            │
│  └──────────┘ └───────────┘ └──────────┘            │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│          Store Layer (mixin architecture)            │
│  AuthStoreMixin · AgentsStoreMixin · CrmStoreMixin   │
│  ConversationsStoreMixin · BillingStoreMixin          │
│  AnalyticsStoreMixin                                 │
│                                                      │
│  SqlAlchemyStore (prod) ←── InMemoryStore (test)     │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    PostgreSQL      Qdrant        Redis
```

## Мультитенантность

- Каждый запрос фильтруется по `tenant_id` на уровне store.
- JWT-токены содержат `tenant_id` и `role`.
- RBAC: 4 роли — `owner`, `admin`, `agent`, `viewer`.
- Row-Level Security (RLS) включён для PostgreSQL.

## Store Architecture (после T3.4)

`SqlAlchemyStore` разбит на домены через Python mixins:
- `AuthStoreMixin` — пользователи, сессии, токены
- `AgentsStoreMixin` — агенты, шаблоны, инструменты
- `CrmStoreMixin` — лиды, сделки, заказы, контакты
- `ConversationsStoreMixin` — диалоги, сообщения
- `BillingStoreMixin` — биллинг, подписки, использование
- `AnalyticsStoreMixin` — аналитика, отчёты

## Guard Rails (безопасность AI)

- Prompt injection detection (RU + EN)
- Toxicity escalation
- Secret leak prevention
- Prohibited claims blocking
- Opt-out/DNC compliance
- Human handoff intent detection
- Tool safety validation
