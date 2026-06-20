# Production service endpoints runbook

These endpoints are local/provider-ready scaffolds. They are safe to run without real provider secrets because they use deterministic local adapters until credentials are configured.

## Readiness

```bash
curl http://localhost:8000/api/v1/readiness
```

The response reports `STORE_BACKEND` plus LLM, Telegram, YooKassa, iiko,
Twilio voice, speech STT/TTS and Asterisk ARI provider readiness. Missing
optional providers are shown as `local_stub`; a provider explicitly requested
through env but missing its required endpoint/secret is shown as
`missing_secret`.

## Required provider environment variables

```dotenv
TELEGRAM_BOT_TOKEN=
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
IIKO_API_LOGIN=
IIKO_API_PASSWORD=
API_PUBLIC_URL=https://api.example.com
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
ASTERISK_ARI_USERNAME=
ASTERISK_ARI_PASSWORD=
LLM_PROVIDER=auto
OPENAI_API_KEY=
VLLM_BASE_URL=http://localhost:8001/v1
VLLM_API_KEY=not-needed
VLLM_MODEL=Qwen/Qwen2.5-7B-Instruct
```

`LLM_PROVIDER=auto` prefers local OpenAI-compatible/vLLM for fast routes when
`VLLM_BASE_URL` is configured, otherwise OpenAI when `OPENAI_API_KEY` is set,
otherwise deterministic mock output for local development.

## Local provider endpoints

All requests require `x-tenant-id`.

- `GET /api/v1/integrations/iiko/menu`
- `POST /api/v1/integrations/iiko/orders`
- `POST /api/v1/integrations/telegram/messages`
- `POST /api/v1/integrations/yookassa/payments`
- `POST /api/v1/integrations/webhooks/sign`
- `POST /api/v1/integrations/webhooks/verify`
- `POST /api/v1/voice/sessions`
- `GET /api/v1/voice/sessions/{session_id}`
- `POST /api/v1/voice/sessions/{session_id}/events`
- `POST /api/v1/voice/sessions/{session_id}/preview-turn`
- `POST /api/v1/voice/sessions/{session_id}/audio?agent_id={agent_id}`
- `POST /api/v1/voice/calls/outbound`
- `POST /api/v1/voice/webhooks/twilio/voice/{agent_id}`
- `POST /api/v1/voice/webhooks/twilio/sms/{agent_id}`
- `POST /api/v1/billing/usage`

`preview-turn` is the safe staging/local voice test: it runs the voice
orchestrator path, writes `VoiceSession.transcript`, persists the conversation
log and returns `conversation_id`. It does not prove real SIP media, STT/TTS
quality, barge-in or call recording. Real phone validation still requires
Twilio/SIP credentials, `API_PUBLIC_URL`, speech provider configuration and
end-to-end call tests.

## SQL-backed runtime

```bash
make infra-up
make migrate
STORE_BACKEND=sqlalchemy DATABASE_URL=postgresql://gaz:gaz@localhost:5432/gaz make api-dev
```

Keep `.env` secrets out of git. Use `.env.example` only for placeholder names.
