# Backup restore drill runbook

This skeleton validates the restore process without production credentials.

## Local dry run

```bash
make backup-restore-drill DRILL_ARGS=--dry-run
make backup-restore-drill
```

The default run creates a synthetic local backup file, records a checksum, and
skips database restore execution.

## With a non-production backup

```bash
BACKUP_FILE=./data/non-prod.dump make backup-restore-drill
```

Only use non-production dumps. If `pg_restore` is installed, the script inspects
the archive with `pg_restore --list`.

## Restore execution

Restore execution is intentionally disabled unless a local throwaway target is
provided:

```bash
DRILL_DATABASE_URL=postgresql://gaz:gaz@localhost:5432/gaz make backup-restore-drill
```

Do not point `DRILL_DATABASE_URL` at shared, staging, or production databases.
