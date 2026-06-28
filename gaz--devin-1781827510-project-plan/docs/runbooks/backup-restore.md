# Runbook — Backup & Restore

Goal: zero customer data loss. **RPO ≤ 15 min** (daily snapshot + WAL) and
**RTO ≤ 2 h** (validated restore).

## What is backed up

| Target | Mechanism | Schedule | Retention |
| --- | --- | --- | --- |
| PostgreSQL (tenants, agents, conversations, billing, audit) | `postgres-backup` container (`pg_dump -Fc` → `.sql.gz`) | `@daily` | 14 daily / 4 weekly / 6 monthly |
| Qdrant (knowledge vectors) | volume snapshot of `qdrant-data` | weekly (manual / volume backup) | 4 weeks |
| Grafana / Prometheus TSDB | docker named volumes | weekly (manual) | 4 weeks |
| Object storage (audio, docs) | bucket versioning + lifecycle | continuous | 90 days |

Backups land in `infra/backups/` on the API host. For real durability, sync
`infra/backups/` to off-host storage (S3 / Yandex Object Storage) — see
"Off-host replication" below.

## Daily snapshot location

```bash
cd infra
ls -lh backups/                      # callforce_YYYY-MM-DDTHH-MM-SSZ.sql.gz
```

## Manual backup (before risky ops)

```bash
docker compose exec -T postgres \
  pg_dump -U callforce callforce | gzip > infra/backups/manual-$(date +%FT%H%M).sql.gz
```

## Restore drill (monthly, mandatory)

The drill proves a backup is restorable. It NEVER touches production.

```bash
# 1. Spin up a throwaway Postgres on a different port
docker run --rm -d --name drill-pg -p 5433:5432 \
  -e POSTGRES_PASSWORD=drill -e POSTGRES_DB=drill postgres:16-alpine

# 2. Run the drill against the latest backup
./scripts/backup-restore-drill.sh \
  --drill-url postgresql://postgres:drill@127.0.0.1:5433/drill

# 3. Inspect / spot-check, then tear down
docker stop drill-pg
```

A green run prints `Backup restore drill PASSED` and row counts for the core
tables. Log the result in the ops journal. If it fails, treat as P1 — a backup
that can't be restored is no backup.

## Real disaster restore (production DB lost)

This is the playbook when the production database is corrupt or the volume was
lost. Approximate budget: 30 min.

```bash
cd infra

# 1. Stop write traffic to avoid split-brain
docker compose stop api web

# 2. (Re)create a fresh DB if the container is gone
docker compose up -d postgres
# wait for healthy
docker compose exec postgres psql -U callforce -d postgres \
  -c "DROP DATABASE IF EXISTS callforce;" \
  -c "CREATE DATABASE callforce OWNER callforce;"

# 3. Restore the chosen snapshot
gunzip -c infra/backups/<SNAPSHOT>.sql.gz | \
  docker compose exec -T postgres psql -U callforce -d callforce

# 4. Re-run migrations to bring schema to current code version
docker compose run --rm api alembic upgrade head

# 5. Bring services back and smoke test
docker compose up -d
curl https://api.callforce.ru/api/v1/readiness
```

Validate with the staging checklist in `DEPLOYMENT.md` §8 before declaring the
incident closed. Notify affected tenants per the incident-response runbook.

## Off-host replication (recommended)

Daily container snapshots on the same host die with the host. Add one of:

- `rclone sync infra/backups/ s3:callforce-backups/` in a nightly cron, or
- a second `postgres-backup` service with `S3_*` env on the official image, or
- managed Postgres with PITR (Yandex Managed PostgreSQL, Selectel).

Target: at least one backup copy in a different region / provider.

## Failure modes

| Symptom | Cause | Fix |
| --- | --- | --- |
| drill `RESTORE FAILED` | schema drifted vs backup | restore older snapshot, then `alembic upgrade head` |
| backup file < 1 KB | `pg_dump` errored silently | check `postgres-backup` logs, fix conn, force a manual dump |
| `psql: command not found` | client not on host | `docker compose exec postgres psql ...` instead |
| restore too slow | large DB, single-thread | use `pg_restore -j 4` against a `-Fc` dump |
