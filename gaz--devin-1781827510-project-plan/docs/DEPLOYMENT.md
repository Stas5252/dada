# DEPLOYMENT.md — Развёртывание CallForce

## Требования

- Python 3.12+
- Node.js 18+ (для frontend)
- PostgreSQL 15+
- Redis 7+
- Qdrant 1.7+

## Локальная разработка

```bash
# 1. Backend
cd apps/api
cp ../../.env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload --port 8000

# 2. Frontend
cd apps/web
npm install
npm run dev

# 3. Worker (фоновые задачи)
cd apps/api
uv run python -m app.worker
```

## Docker Compose (рекомендуется)

```bash
docker compose up -d
```

Контейнеры: `api`, `web`, `worker`, `postgres`, `redis`, `qdrant`.

## Переменные окружения

См. `.env.example` для полного списка. Критические для production:

| Переменная | Описание | Обязательна? |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | ✅ Да |
| `ACCESS_TOKEN_SECRET` | Секрет для JWT | ✅ Да |
| `OPENAI_API_KEY` | Ключ OpenAI | ⚠️ Для LLM |
| `YANDEX_API_KEY` | Ключ Yandex SpeechKit | ⚠️ Для STT/TTS |
| `QDRANT_URL` | URL Qdrant | ✅ Для prod |
| `REDIS_URL` | URL Redis | ✅ Для очередей |
| `YOOKASSA_SHOP_ID` | ID магазина YooKassa | ⚠️ Для платежей |
| `TWILIO_ACCOUNT_SID` | SID Twilio | ⚠️ Для телефонии |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | ⚠️ Для Telegram |
| `APP_ENV` | `local` / `staging` / `production` | ✅ Да |

## Проверка готовности

```bash
# Health check
curl http://localhost:8000/api/v1/system/health

# Readiness matrix (все провайдеры)
curl http://localhost:8000/api/v1/system/readiness
```

## Масштабирование

- API: горизонтально через load balancer
- Worker: несколько инстансов Arq
- PostgreSQL: read replicas
- Qdrant: кластерный режим
- Redis: Sentinel / Redis Cluster
