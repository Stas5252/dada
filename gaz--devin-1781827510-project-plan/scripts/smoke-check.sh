#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/smoke-check.sh [--dry-run]

Checks locally running app endpoints without requiring real secrets.

Environment:
  API_URL   API base URL. Defaults to http://localhost:8000.
  WEB_URL   Web base URL. Defaults to http://localhost:3000.
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

api_url="${API_URL:-http://localhost:8000}"
web_url="${WEB_URL:-http://localhost:3000}"

if [[ "$dry_run" == "1" ]]; then
  cat <<DRYRUN
Smoke check plan:
1. GET ${api_url}/api/v1/health
2. GET ${web_url}/
DRYRUN
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for smoke checks." >&2
  exit 1
fi

curl --fail --silent --show-error --max-time 5 "${api_url}/api/v1/health" >/dev/null
curl --fail --silent --show-error --max-time 5 "${web_url}/" >/dev/null

echo "Smoke checks passed."
