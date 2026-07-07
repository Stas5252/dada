# Environment variables

Use `.env.example` as the source template. Never commit real `.env` files.

## Core

| Variable | Purpose | Production note |
| --- | --- | --- |
| `APP_ENV` | `local`, `test`, `development`, `staging`, `production` | Must be `production` in prod |
| `API_HOST`, `API_PORT`, `WEB_PORT` | Bind ports | Usually container defaults |
| `CORS_ORIGINS` | Allowed web/widget origins | Must be explicit domains |
| `API_PUBLIC_URL` | Public backend URL for webhooks/calls | Must be HTTPS |
| `NEXT_PUBLIC_API_URL` | Frontend API target | Must point to public API |

## Data stores

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection |
| `STORE_BACKEND` | `sqlalchemy` for durable store |
| `REDIS_URL` | Redis default URL |
| `RATE_LIMIT_ENABLED` | Enables public/API rate limits; set `false` only for local repeated e2e runs |
| `RATE_LIMIT_STORAGE_URI` | Redis/memory rate limit backend |
| `QDRANT_URL` | Qdrant vector DB |
| `QDRANT_COLLECTION_NAME` | Knowledge collection |
| `OBJECT_STORAGE_ENDPOINT` | S3/MinIO endpoint |
| `OBJECT_STORAGE_BUCKET` | Upload/recording bucket |

## Security

| Variable | Purpose | Production note |
| --- | --- | --- |
| `ACCESS_TOKEN_SECRET` | JWT signing | Strong random secret required |
| `REFRESH_TOKEN_TTL_DAYS` | Refresh token lifetime | Set by security policy |
| `ACCESS_TOKEN_TTL_MINUTES` | Access token lifetime | Short TTL recommended |
| `ENCRYPTION_KEY` | Integration secret encryption | Strong key required |
| `WEBHOOK_SIGNING_SECRET` | Custom webhook signatures | Rotate when leaked |
| `ALLOW_LEGACY_TENANT_HEADER` | Header-based tenant fallback | Must be `false` outside local/test |

## AI providers

| Variable | Purpose |
| --- | --- |
| `LLM_PROVIDER` | `auto`, `openai`, local provider mode |
| `OPENAI_API_KEY` | OpenAI key |
| `OPENAI_FAST_MODEL` | Fast model |
| `OPENAI_SMART_MODEL` | Smart model |
| `VLLM_BASE_URL` | Local/OpenAI-compatible provider |
| `VLLM_API_KEY` | Local provider key if required |
| `VLLM_MODEL` | Local model name |

## Voice and telephony

| Variable | Purpose |
| --- | --- |
| `TWILIO_ACCOUNT_SID` | Twilio account |
| `TWILIO_AUTH_TOKEN` | Twilio auth |
| `TWILIO_PHONE_NUMBER` | Outbound number |
| `ASTERISK_ARI_URL` | Asterisk ARI URL |
| `ASTERISK_ARI_USERNAME` | ARI user |
| `ASTERISK_ARI_PASSWORD` | ARI password |
| `STT_MODEL_PATH` | Local STT model path |
| `TTS_MODEL_PATH` | Local TTS model path |

## Channels, billing and integrations

| Variable | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `YOOKASSA_SHOP_ID` | YooKassa shop |
| `YOOKASSA_SECRET_KEY` | YooKassa secret |
| `IIKO_API_LOGIN` | iikoCloud API login |
| `IIKO_API_PASSWORD` | iikoCloud password if used |

## Launch readiness checks

Use `GET /api/v1/tenants/{tenant_id}/settings/integration-readiness` from an authenticated owner/admin/operator session before a pilot launch. The endpoint returns configured/missing status and setting names only; it must not expose provider secret values.

Use `GET /api/v1/tenants/{tenant_id}/settings/channel-webhooks` to verify Telegram/VK/WhatsApp callback URLs, public HTTPS readiness and missing tenant settings. Tenant-level channel secrets include `whatsapp_app_secret` and optional `vk_secret_key`; they are stored in tenant settings and are never returned by diagnostics.

## Production domains

| Variable | Purpose |
| --- | --- |
| `APP_DOMAIN` | Main app domain |
| `API_DOMAIN` | API domain |
| `GRAFANA_DOMAIN` | Grafana domain |
| `ACME_EMAIL` | TLS certificate email |
