# CallForce — Production Deployment Guide

This guide explains how to deploy CallForce on a production VPS using Docker
Compose + Traefik (automatic HTTPS via Let's Encrypt), with daily PostgreSQL
backups, monitoring (Prometheus/Grafana/Alertmanager) and structured logging.

## Prerequisites

1. A Linux server (Ubuntu 22.04+ recommended) with **at least 4 GB RAM, 2 vCPU,
   40 GB SSD**. Voice/GPU workloads need more — see Voice section below.
2. Docker Engine 24+ and Docker Compose v2 installed.
3. DNS A-records pointing to your server's public IP for:
   - `app.callforce.ru` (Next.js web app + marketing site)
   - `api.callforce.ru` (FastAPI backend)
   - `grafana.callforce.ru` (Grafana, optional)
4. Ports **80 + 443** open inbound (Traefik needs :80 for the ACME TLS
   challenge; all real traffic is redirected to :443).

## 1. Setup

```bash
git clone https://github.com/Stas5252/dada.git callforce
cd callforce
```

Create the production env file **from the production template** (not the local
one — local `.env.example` keeps `STORE_BACKEND=memory` and demo seeds on):

```bash
cp .env.prod.example .env
nano .env
```

You MUST replace every `__REPLACE_WITH_*__` placeholder. Generate secrets:

```bash
# 64-char hex secrets (ACCESS_TOKEN_SECRET, JWT_SECRET, WEBHOOK_SIGNING_SECRET)
openssl rand -hex 32

# Fernet key for ENCRYPTION_KEY (used by app/encryption.py)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Strong Postgres / Grafana password
openssl rand -base64 24
```

Set the domains (`APP_DOMAIN`, `API_DOMAIN`, `GRAFANA_DOMAIN`, `ACME_EMAIL`).

Pick an LLM provider (`LLM_PROVIDER=openai` with a key, or `LLM_PROVIDER=local`
with `VLLM_BASE_URL`).

## 2. Prepare Let's Encrypt storage

```bash
mkdir -p infra/letsencrypt
touch infra/letsencrypt/acme.json
chmod 600 infra/letsencrypt/acme.json
```

## 3. Launch

```bash
cd infra
docker compose up -d --build
```

The `api` container runs `alembic upgrade head` before starting Uvicorn, so the
PostgreSQL schema is migrated automatically on every deploy.

Traefik provisions TLS certificates for each domain on first request.

## 4. Verify

```bash
# All services healthy
docker compose ps

# Backend
curl https://api.callforce.ru/health
curl https://api.callforce.ru/api/v1/readiness   # shows store_backend=sqlalchemy

# Web
curl -I https://app.callforce.ru

# Grafana (login: admin / GRAFANA_PASSWORD)
open https://grafana.callforce.ru/dashboards   # "CallForce API Overview" auto-provisioned
```

## 5. Backups (automatic + manual)

A `postgres-backup` container takes a daily gzipped dump and keeps:
- 14 daily, 4 weekly, 6 monthly snapshots in `infra/backups/`.

Manual backup / restore drill:

```bash
# Create a one-off backup now
docker compose exec postgres pg_dump -U callforce callforce | gzip > infra/backups/manual-$(date +%F).sql.gz

# Restore drill (against a throwaway DB — never against production)
DRILL_DATABASE_URL=postgresql://drill:drill@127.0.0.1:5433/drill \
  ./scripts/backup-restore-drill.sh infra/backups/manual-$(date +%F).sql.gz
```

Validate a backup is restorable at least once a month. See
`docs/runbooks/backup-restore.md`.

## 6. Monitoring & alerting

| Signal | Where |
| --- | --- |
| API p50/p95 latency, error rate, RPS | Grafana → "CallForce API Overview" |
| Per-service `up` | Prometheus / Alertmanager |
| 5xx > 5% for 2m | `HighApiErrorRate` alert |
| p95 > 2s for 2m | `HighApiLatency` alert |
| Any target down 1m | `InstanceDown` alert |
| App exceptions | Sentry (`SENTRY_DSN`) |

Wire Alertmanager to a real receiver (Slack/Telegram/email) by editing
`infra/alertmanager/alertmanager.yml`.

## 7. Updating

```bash
cd infra
git pull
docker compose up -d --build          # rebuilds images, re-runs migrations
docker compose logs -f api            # watch startup
```

Rollback:

```bash
# Revert code
git checkout <previous-commit>
docker compose up -d --build
# Restore DB if a migration must be reverted
gunzip -c infra/backups/<file>.sql.gz | docker compose exec -T postgres psql -U callforce callforce
```

## 8. Staging

Deploy the same `infra/docker-compose.yml` on a second server with
`APP_ENV=staging`, separate DNS (`staging.callforce.ru`), a separate
`POSTGRES_DB=callforce_staging`, and `SEED_DEMO_DATA=true`. Never share secrets
or DBs between staging and production.

## 9. Voice / GPU workloads (optional)

Asterisk + a local STT/TTS GPU server are heavier and not required for chat-only
tenants. Run them on a separate host with a GPU (e.g. A10) and point
`ASTERISK_ARI_URL` / `VLLM_BASE_URL` at it from the API host. See
`docs/runbooks/voice-realtime.md`.

## Troubleshooting

- **Traefik can't get a certificate**: confirm port 80 is reachable from the
  internet and DNS resolves before you bring the stack up. Check
  `docker compose logs traefik`.
- **`api` restart-loops**: usually a missing/weak `ACCESS_TOKEN_SECRET`. The app
  refuses to boot in production with the default secret.
- **`store_backend=memory` in readiness**: the api container didn't receive
  `STORE_BACKEND=sqlalchemy`. Confirm `.env` is mounted and the compose project
  is `infra/`.
- **Out of disk**: `docker compose exec postgres vacuumdb --all -z` and prune
  old `infra/backups/`.
