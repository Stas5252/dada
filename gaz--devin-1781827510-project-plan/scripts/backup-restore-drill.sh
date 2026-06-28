#!/usr/bin/env bash
# =============================================================================
# CallForce backup restore drill
# Validates that a PostgreSQL backup can actually be restored, end-to-end.
# Safe by default: only restores into a THROWAWAY database (never production).
# =============================================================================
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/backup-restore-drill.sh [BACKUP_FILE] [--drill-url URL] [--dry-run]

Validates the backup restore drill path end-to-end against a throwaway DB.

Arguments:
  BACKUP_FILE       Path to a .sql.gz or .sql dump (default: latest in infra/backups)

Options:
  --drill-url URL   Throwaway PostgreSQL URL to restore into (required for a real restore).
                    Must match one of the safe patterns: localhost / 127.0.0.1 / *.local / *drill*.
  --dry-run         Print the plan and a checksum only, do not restore.

Environment:
  DRILL_DATABASE_URL   Same as --drill-url.
  RESTORE_DRILL_WORKDIR  Scratch dir (default: mktemp).

Examples:
  # Dry run against the latest daily backup
  ./scripts/backup-restore-drill.sh --dry-run

  # Real restore into a throwaway container
  docker run --rm -d --name drill-pg -p 5433:5432 \
    -e POSTGRES_PASSWORD=drill -e POSTGRES_DB=drill postgres:16-alpine
  ./scripts/backup-restore-drill.sh \
    infra/backups/callforce-2026-06-21.sql.gz \
    --drill-url postgresql://postgres:drill@127.0.0.1:5433/drill
USAGE
}

backup_file=""
drill_url="${DRILL_DATABASE_URL:-}"
dry_run=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry_run=1; shift ;;
    --drill-url) drill_url="$2"; shift 2 ;;
    --drill-url=*) drill_url="${1#*=}"; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)
      if [[ -z "$backup_file" ]]; then
        backup_file="$1"
      else
        echo "Unexpected argument: $1" >&2; exit 2
      fi
      shift ;;
  esac
done

# Default: pick the newest backup in infra/backups
if [[ -z "$backup_file" ]]; then
  backups_dir="$(dirname "$0")/../infra/backups"
  backup_file="$(ls -1t "$backups_dir"/*.sql.gz "$backups_dir"/*.sql 2>/dev/null | head -n1 || true)"
  if [[ -z "$backup_file" ]]; then
    echo "No BACKUP_FILE given and none found in $backups_dir." >&2
    exit 1
  fi
  echo "Using latest backup: $backup_file"
fi

if [[ ! -r "$backup_file" ]]; then
  echo "Backup file is not readable: $backup_file" >&2
  exit 1
fi

workdir="${RESTORE_DRILL_WORKDIR:-$(mktemp -d)}"
cleanup=0
if [[ -z "${RESTORE_DRILL_WORKDIR:-}" ]]; then
  cleanup=1
  trap 'rm -rf "$workdir"' EXIT
fi
mkdir -p "$workdir"

# 1. Integrity: checksum + size
echo "== Backup integrity =="
sha256sum "$backup_file" | tee "$workdir/backup.sha256"
size_bytes=$(wc -c < "$backup_file")
echo "size_bytes=$size_bytes"
if [[ "$size_bytes" -lt 100 ]]; then
  echo "Backup is suspiciously small (<100 bytes). Aborting." >&2
  exit 1
fi

# 2. Can we read it as a SQL stream?
echo "== Dump readability =="
if [[ "$backup_file" == *.gz ]]; then
  if ! gunzip -t "$backup_file"; then
    echo "gzip integrity check FAILED for $backup_file" >&2
    exit 1
  fi
  decompress=(gunzip -c "$backup_file")
else
  decompress=(cat "$backup_file")
fi

head_dump="$workdir/head.sql"
"${decompress[@]}" | head -n 50 > "$head_dump"
echo "First lines of dump:"
sed -n '1,8p' "$head_dump"

if [[ "$dry_run" == "1" ]]; then
  cat <<DRYRUN

== DRY RUN: would restore into ==
  ${drill_url:-<no --drill-url; nothing would be restored>}
DRYRUN
  echo "Backup restore drill DRY RUN completed (no restore performed)."
  exit 0
fi

# 3. Real restore — only into a verified-throwaway target
if [[ -z "$drill_url" ]]; then
  echo "No --drill-url given; skipping live restore." >&2
  echo "Pass --drill-url postgresql://...@127.0.0.1:<port>/drill for a full drill." >&2
  exit 3
fi

case "$drill_url" in
  *localhost*|*127.0.0.1*|*::1*|*.local*|*drill*)
    : ;; # safe target
  *)
    echo "Refusing to restore: --drill-url must target localhost/127.0.0.1/*.local/*drill*." >&2
    exit 1
    ;;
esac

if ! command -v psql >/dev/null 2>&1; then
  echo "psql not found in PATH; install postgresql-client to run a live drill." >&2
  exit 1
fi

echo "== Restoring into throwaway DB =="
echo "target: $drill_url"

# Restore the dump. --set ON_ERROR_STOP=1 makes any SQL error fail the drill.
if ! "${decompress[@]}" | PGPASSWORD="${PGPASSWORD:-}" psql "$drill_url" -v ON_ERROR_STOP=1 -q; then
  echo "RESTORE FAILED." >&2
  exit 1
fi

# 4. Sanity: count rows in core tables (names are tolerant — drill DB may differ)
echo "== Post-restore sanity =="
for table in tenants users agents conversations; do
  count=$(psql "$drill_url" -tAc "SELECT count(*) FROM $table;" 2>/dev/null || echo "n/a")
  echo "  $table: $count rows"
done

echo
echo "Backup restore drill PASSED. Drop the throwaway DB when done:"
echo "  psql postgres://... -c 'DROP DATABASE drill;'"
