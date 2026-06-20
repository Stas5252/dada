# Migration dry-run runbook

This skeleton provides a safe place for migration validation before real
migration tooling is added.

## Local dry run

```bash
make migration-dry-run DRILL_ARGS=--dry-run
make migration-dry-run
```

The script validates that `migrations/` exists. Until Alembic or another
migration runner is configured, it exits successfully after reporting that no
runner is available.

## Future Alembic path

When `alembic.ini` is added, the script will generate SQL with:

```bash
DATABASE_URL="$MIGRATION_DRY_RUN_DATABASE_URL" alembic upgrade head --sql
```

`MIGRATION_DRY_RUN_DATABASE_URL` must point to a local throwaway database.

## Apply SQL migrations locally

After local PostgreSQL is running and `.env` points `DATABASE_URL` at the local database:

```bash
make migrate
```

The runner applies `migrations/versions/*.sql` in lexical order and records applied filenames in `schema_migrations`.
