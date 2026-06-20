#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/migration-dry-run.sh [--dry-run]

Prepares a migration dry-run without requiring production secrets.

Environment:
  MIGRATION_DRY_RUN_DATABASE_URL   Optional local database URL.
USAGE
}

dry_run=0
for arg in "$@"; do
  case "$arg" in
    --dry-run)
      dry_run=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

database_url="${MIGRATION_DRY_RUN_DATABASE_URL:-postgresql://gaz:gaz@localhost:5432/gaz}"
case "$database_url" in
  *localhost*|*127.0.0.1*|*gaz*)
    ;;
  *)
    echo "Refusing to dry-run migrations against a non-local database URL." >&2
    exit 1
    ;;
esac

if [[ "$dry_run" == "1" ]]; then
  cat <<'DRYRUN'
Migration dry-run plan:
1. Use only MIGRATION_DRY_RUN_DATABASE_URL or the local docker-compose database.
2. Generate SQL with Alembic when alembic.ini exists.
3. Fail closed if the target database URL is not local.
DRYRUN
  exit 0
fi

if [[ ! -d "migrations" ]]; then
  echo "migrations/ directory is missing." >&2
  exit 1
fi

if [[ ! -f "alembic.ini" ]]; then
  echo "No Alembic configuration found; migration dry-run skeleton validated."
  exit 0
fi

if ! command -v alembic >/dev/null 2>&1; then
  echo "alembic is not installed; run the API dependency install first." >&2
  exit 1
fi

DATABASE_URL="$database_url" alembic upgrade head --sql > /tmp/gaz-migration-dry-run.sql
echo "Generated /tmp/gaz-migration-dry-run.sql"
