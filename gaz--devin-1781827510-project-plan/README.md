# CallForce

**AI-агенты нового поколения для звонков и чатов.**

CallForce — российская платформа автоматизации коммуникаций: входящие/исходящие голосовые звонки, чат-боты, RAG база знаний, Action Engine для интеграций, визуальный конструктор сценариев, операторская консоль, аналитика и биллинг.

> 🔥 **Лучше, чем Bland.ai** — мультиканальность, русский язык, интеграции с iiko/CRM/1C, визуальный билдер, SaaS кабинет, 152-ФЗ compliance.

Подробный продуктовый и инженерный план: [`PROJECT_COMPLETION_PLAN.md`](PROJECT_COMPLETION_PLAN.md).

## Архитектура

```
callforce/
  apps/
    api/          # FastAPI backend (Python 3.12+)
    web/          # Next.js frontend (TypeScript)
  packages/
    shared-types/ # Общие TypeScript типы
    ui/           # UI-компоненты
  infra/          # Docker Compose (PostgreSQL, Redis, Qdrant, MinIO)
  migrations/     # SQL-миграции
  scripts/        # Утилиты: seed, backup, smoke checks
  tests/          # Интеграционные тесты
  docs/           # Документация, стратегия, runbooks
```

## Что умеет CallForce

### Каналы (Voice + Chat)
- 📞 **Голосовые AI-агенты** — входящие/исходящие звонки через SIP
- 💬 **Telegram, WhatsApp, VK, web-виджет** — единая модель диалога
- 🔄 **Cold calling** — массовые исходящие звонки с AI

### Intelligence
- 🧠 **RAG база знаний** — Qdrant vector search, citations, coverage audit
- ⚡ **Action Engine** — iiko, r_keeper, AmoCRM, Bitrix24, 1C, webhooks
- 🎨 **Визуальный конструктор** — React Flow drag-n-drop сценарии

### Enterprise
- 🛡️ **Multi-tenant** — tenant isolation, RBAC, audit logs
- 💳 **Биллинг** — ЮKassa, тарифы, usage tracking
- 📊 **Аналитика** — automation rate, quality, cost, topics
- 🏥 **Операторская консоль** — live handoff, context transfer

### LLM Support
- 🤖 **Локальные модели** — vLLM, Faster-Whisper, XTTS/Kokoro
- ☁️ **API провайдеры** — OpenAI, Anthropic и другие

## Требования

- Python 3.12+
- Node.js 22+
- npm 10+
- Docker 27+
- uv

## Быстрый старт

```bash
cp .env.example .env
make install
make test
make lint
make typecheck
make build
```

Demo seed:

```bash
make seed-demo
```

Локальная инфраструктура:

```bash
make infra-up    # PostgreSQL, Redis, Qdrant, MinIO
make api-dev     # FastAPI на :8000
make web-dev     # Next.js на :3000
```

## CallForce API

```
POST /api/v1/auth/register     POST /api/v1/auth/login
POST /api/v1/auth/refresh      POST /api/v1/auth/logout
GET  /api/v1/auth/me           POST /api/v1/auth/login/mfa
POST /api/v1/auth/mfa/setup    POST /api/v1/auth/mfa/verify
POST /api/v1/auth/mfa/recovery-codes
POST /api/v1/auth/mfa/disable
POST /api/v1/auth/verify-email
POST /api/v1/auth/request-password-reset
POST /api/v1/auth/reset-password
GET  /api/v1/tenants/{id}/dashboard
GET  /api/v1/agents            POST /api/v1/agents
GET  /api/v1/agents/{id}       PATCH /api/v1/agents/{id}
POST /api/v1/agents/{id}/publish
GET  /api/v1/knowledge/sources
POST /api/v1/knowledge/sources
POST /api/v1/knowledge/upload
POST /api/v1/knowledge/sources/{id}/ingest
GET  /api/v1/knowledge/ingestion/jobs
GET  /api/v1/knowledge/qdrant/contract
GET  /api/v1/conversations     GET /api/v1/conversations/{id}
POST /api/v1/chat/mock
GET  /api/v1/readiness
```

## Тарифы

| Тариф | Цена | Включено |
| --- | --- | --- |
| Start | 2 990 ₽/мес | 300 диалогов, чат, 1 агент |
| Business | 7 990 ₽/мес | 1000 диалогов, голос, iiko, 3 канала |
| Pro | 19 990 ₽/мес | 4000 диалогов, CRM, сценарии, аналитика |
| Enterprise | от 49 990 ₽/мес | Безлимит, SLA 99.9%, custom |

## Лицензия

Proprietary. © 2026 CallForce.
