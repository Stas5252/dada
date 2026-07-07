# ENVIRONMENT.md — Переменные окружения CallForce

Полный справочник переменных окружения. См. также `.env.example` в корне проекта.

## Core

| Переменная | По умолчанию | Описание |
|---|---|---|
| `APP_ENV` | `local` | Окружение: `local`, `development`, `staging`, `production` |
| `DATABASE_URL` | `postgresql://callforce:callforce@localhost:5432/callforce` | PostgreSQL connection string |
| `ACCESS_TOKEN_SECRET` | `local-development-token-secret` | ⚠️ Обязательно сменить в prod |
| `ACCESS_TOKEN_TTL_MINUTES` | `15` | TTL access-токена |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | TTL refresh-токена |
| `STORE_BACKEND` | `sqlalchemy` | Бэкенд хранилища: `sqlalchemy` / `memory` |
| `SEED_DEMO_DATA` | `true` | Загружать демо-данные |
| `API_PUBLIC_URL` | `http://localhost:8000` | Публичный URL API (для вебхуков) |
| `CORS_ORIGINS` | `http://localhost:3000` | Разрешённые CORS origins |

## LLM

| Переменная | По умолчанию | Описание |
|---|---|---|
| `LLM_PROVIDER` | `auto` | `auto` / `openai` / `vllm` |
| `OPENAI_API_KEY` | — | Ключ OpenAI API |
| `OPENAI_FAST_MODEL` | `gpt-4o-mini` | Быстрая модель для простых запросов |
| `OPENAI_SMART_MODEL` | `gpt-4o` | Умная модель для сложных запросов |
| `VLLM_BASE_URL` | — | URL self-hosted vLLM |
| `VLLM_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | Модель для vLLM |
| `LLM_TEMPERATURE` | `0.3` | Температура генерации |
| `LLM_MAX_TOKENS` | `1024` | Максимум токенов |
| `LLM_TIMEOUT_SECONDS` | `30.0` | Таймаут запроса к LLM |

## Речь (STT/TTS)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `YANDEX_API_KEY` | — | Ключ Yandex SpeechKit (приоритет для RU) |
| `DEEPGRAM_API_KEY` | — | Ключ Deepgram (fallback STT) |
| `ELEVENLABS_API_KEY` | — | Ключ ElevenLabs (TTS) |

## Каналы

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | Токен Telegram бота |
| `TWILIO_ACCOUNT_SID` | — | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | — | Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | — | Twilio номер телефона |
| `ASTERISK_ARI_USERNAME` | — | Asterisk ARI логин |
| `ASTERISK_ARI_PASSWORD` | — | Asterisk ARI пароль |

## Платежи и интеграции

| Переменная | По умолчанию | Описание |
|---|---|---|
| `YOOKASSA_SHOP_ID` | — | ID магазина YooKassa |
| `YOOKASSA_SECRET_KEY` | — | Секрет YooKassa |
| `IIKO_API_LOGIN` | — | Логин iikoCloud API |
| `IIKO_API_PASSWORD` | — | Пароль iikoCloud API |

## Инфраструктура

| Переменная | По умолчанию | Описание |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| `QDRANT_URL` | — | Qdrant URL (обязателен для prod) |
| `QDRANT_COLLECTION_NAME` | `callforce_knowledge_chunks` | Коллекция Qdrant |
| `QDRANT_VECTOR_SIZE` | `384` | Размерность эмбеддингов |
| `SENTRY_DSN` | — | DSN Sentry для мониторинга |
| `OTEL_ENABLED` | `false` | Включить OpenTelemetry |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP эндпоинт |

## Email (SMTP)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `SMTP_HOST` | — | SMTP сервер |
| `SMTP_PORT` | `587` | SMTP порт |
| `SMTP_USER` | — | SMTP логин |
| `SMTP_PASSWORD` | — | SMTP пароль |
| `SMTP_FROM` | `noreply@callforce.local` | Адрес отправителя |
| `SMTP_USE_TLS` | `true` | Использовать TLS |
