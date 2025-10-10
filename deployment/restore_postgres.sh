#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <dump-file>" >&2
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL not set" >&2
  exit 1
fi

DUMP="$1"
pg_restore --clean --no-owner -d "$DATABASE_URL" "$DUMP"
echo "Restore complete"

