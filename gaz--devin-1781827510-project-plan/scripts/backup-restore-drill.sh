#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/backup-restore-drill.sh [--dry-run]

Validates the backup restore drill path without requiring production secrets.

Environment:
  BACKUP_FILE             Optional local dump/archive to inspect.
  RESTORE_DRILL_WORKDIR   Optional scratch directory. Defaults to mktemp.
  DRILL_DATABASE_URL      Optional local throwaway database URL for future restore tests.
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

if [[ "$dry_run" == "1" ]]; then
  cat <<'DRYRUN'
Backup restore drill plan:
1. Select a non-production BACKUP_FILE or create a synthetic local sample.
2. Verify the archive is readable and record its checksum.
3. Inspect the archive with pg_restore --list when a PostgreSQL dump is supplied.
4. Restore only into a throwaway local database supplied via DRILL_DATABASE_URL.
DRYRUN
  exit 0
fi

workdir="${RESTORE_DRILL_WORKDIR:-}"
cleanup_workdir=0
if [[ -z "$workdir" ]]; then
  workdir="$(mktemp -d)"
  cleanup_workdir=1
fi
if [[ "$cleanup_workdir" == "1" ]]; then
  trap 'rm -rf "$workdir"' EXIT
fi
mkdir -p "$workdir"

backup_file="${BACKUP_FILE:-$workdir/gaz-synthetic-backup.dump}"
if [[ -z "${BACKUP_FILE:-}" ]]; then
  {
    echo "gaz synthetic backup"
    date -u +"created_at=%Y-%m-%dT%H:%M:%SZ"
    echo "scope=restore-drill"
  } > "$backup_file"
fi

if [[ ! -r "$backup_file" ]]; then
  echo "Backup file is not readable: $backup_file" >&2
  exit 1
fi

checksum_file="$workdir/backup.sha256"
sha256sum "$backup_file" | tee "$checksum_file"

if command -v pg_restore >/dev/null 2>&1 && [[ -n "${BACKUP_FILE:-}" ]]; then
  pg_restore --list "$backup_file" >/dev/null
else
  echo "pg_restore inspection skipped; no real PostgreSQL archive was provided."
fi

if [[ -n "${DRILL_DATABASE_URL:-}" ]]; then
  case "$DRILL_DATABASE_URL" in
    *localhost*|*127.0.0.1*|*gaz*|*postgres*)
      echo "DRILL_DATABASE_URL is set for a local throwaway restore target."
      ;;
    *)
      echo "DRILL_DATABASE_URL must point to a local throwaway database." >&2
      exit 1
      ;;
  esac
else
  echo "Restore execution skipped; set DRILL_DATABASE_URL for a local throwaway target."
fi

echo "Backup restore drill skeleton completed."
