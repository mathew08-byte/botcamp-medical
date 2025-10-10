#!/usr/bin/env bash
set -euo pipefail

echo "QA Smoke:"
echo "1) /ready endpoint"
curl -sfL ${HEALTHCHECK_URL:-http://localhost:8000}/ready || (echo "ready failed" && exit 1)

echo "2) DB ping via migrate script (no-op if up-to-date)"
if [[ -n "${DATABASE_URL:-}" ]]; then
  ./deployment/migrate.sh || true
fi

echo "3) Basic logs tail (docker compose)"
if command -v docker >/dev/null 2>&1; then
  docker compose -f deployment/docker-compose.yml ps || true
fi

echo "✅ Smoke complete"

