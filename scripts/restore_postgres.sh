#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup-file.sql.gz>" >&2
  exit 1
fi

if [ -z "${DB_URL:-}" ]; then
  echo "DB_URL env var required" >&2
  exit 1
fi

infile="$1"
gunzip -c "$infile" | psql "$DB_URL"
echo "Restore completed from $infile"


