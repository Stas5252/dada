# Smoke checks runbook

Smoke checks verify that the local API and web app are reachable without real
secrets.

## Dry run

```bash
make smoke-check DRILL_ARGS=--dry-run
```

## Full local check

Start local services first:

```bash
make infra-up
make api-dev
make web-dev
```

Then run:

```bash
make smoke-check
```

Defaults:

- `API_URL=http://localhost:8000`
- `WEB_URL=http://localhost:3000`

Override these values only for non-production environments.

## Web widget check

The local demo widget agent is:

```text
389a4f13-05d3-5860-af9f-69bd9ce2493a
```

Required local env:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WIDGET_AGENT_ID=389a4f13-05d3-5860-af9f-69bd9ce2493a
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Smoke the API path:

```bash
curl -X POST "$API_URL/api/v1/widget/chat/389a4f13-05d3-5860-af9f-69bd9ce2493a" \
  -H "content-type: application/json" \
  -d '{"session_id":"smoke_widget_session_123","message":"Сколько стоит доставка?"}'
```

The response must include `conversation_id` and `response`; repeated requests
with the same `session_id` should reuse the same conversation.
