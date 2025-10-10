#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL not set" >&2
  exit 1
fi

STAMP=$(date +%F-%H%M)
OUT="backup-${STAMP}.dump"
pg_dump --format=custom -f "$OUT" "$DATABASE_URL"
echo "Backup created: $OUT"

if [[ -n "${S3_BUCKET:-}" ]]; then
  echo "Uploading to s3://$S3_BUCKET/$OUT"
  aws s3 cp "$OUT" "s3://$S3_BUCKET/$OUT"
fi

