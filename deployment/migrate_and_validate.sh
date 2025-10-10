#!/usr/bin/env bash
set -euo pipefail

STAMP=$(date +%F-%H%M%S)
export DATABASE_URL=${DATABASE_URL:-}
if [[ -z "${DATABASE_URL}" ]]; then
  echo "DATABASE_URL not set" >&2
  exit 1
fi

./deployment/backup_postgres.sh || true

if ! alembic upgrade head; then
  echo "Migration failed; attempting restore"
  # Note: implement selection of latest backup path in your environment
  ./deployment/restore_postgres.sh latest_good.dump || true
  ./deployment/alert.sh "🚨 Migration failed at ${STAMP}; restored previous DB"
  exit 1
fi

if [ -f tests/smoke/run_smoke_tests.py ]; then
  if ! python tests/smoke/run_smoke_tests.py; then
    ./deployment/alert.sh "🚨 Smoke tests failed post-migration at ${STAMP}"
    exit 1
  fi
fi

echo "✅ Migration and validation succeeded"

