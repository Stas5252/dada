# Deployment

## Local development

Requirements:

- Python 3.12+
- Node.js 22+
- npm 10+
- Docker 27+ for full infrastructure
- uv for Python dependency sync

Minimal app-only local run:

```powershell
cd apps/api
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

```powershell
cd apps/web
set "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" && npm run dev -- --hostname 127.0.0.1 --port 3000
```

Full local infrastructure:

```bash
cp .env.example .env
make infra-up
make migrate
make seed-demo
make api-dev
make web-dev
```

## Production compose

Production compose file:

```bash
infra/docker-compose.yml
```

It includes:

- Traefik with HTTPS.
- PostgreSQL.
- Redis.
- Qdrant.
- API.
- Web.
- Prometheus.
- Alertmanager.
- Grafana.
- PostgreSQL backup container.

Production checklist:

1. Create `.env` from `.env.example`.
2. Replace all local/default secrets.
3. Set `APP_ENV=production`.
4. Set domains: `APP_DOMAIN`, `API_DOMAIN`, `GRAFANA_DOMAIN`.
5. Set `ACME_EMAIL`.
6. Set provider credentials only through secure env/secrets.
7. Run `docker compose -f infra/docker-compose.yml config`.
8. Run `docker compose -f infra/docker-compose.yml up -d --build`.
9. Verify `/api/v1/health` and `/api/v1/readiness`.
10. Run smoke checks.

## Release gates

Before deploy:

- backend lint/type/tests pass;
- frontend lint/type/build pass;
- security scans pass;
- migrations are reviewed;
- backup restore procedure is known;
- external credentials are configured;
- `ALLOW_LEGACY_TENANT_HEADER=false` in staging/production;
- `SEED_DEMO_DATA=false` in production.

After deploy:

- health/readiness pass;
- login/register smoke passes;
- at least one agent testbed run passes;
- one channel webhook smoke passes;
- one billing sandbox smoke passes before enabling real billing;
- alerts are firing to the correct destination.
