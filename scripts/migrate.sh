#!/usr/bin/env bash
set -euo pipefail

retries=3
for i in $(seq 1 $retries); do
  echo "[migrate] Attempt $i"
  alembic upgrade head && exit 0 || true
  sleep $((i*2))
done
echo "[migrate] Failed after $retries attempts" >&2
exit 1


