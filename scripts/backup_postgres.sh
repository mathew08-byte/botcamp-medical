#!/usr/bin/env bash
set -euo pipefail

if [ -z "${DB_URL:-}" ]; then
  echo "DB_URL env var required" >&2
  exit 1
fi

ts=$(date +%Y%m%d-%H%M%S)
outfile="postgres-backup-$ts.sql.gz"

pg_dump "$DB_URL" | gzip -9 > "$outfile"
echo "Backup written to $outfile"


