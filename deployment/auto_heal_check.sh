#!/usr/bin/env bash
set -euo pipefail

HEALTH_URL=${HEALTH_URL:-http://localhost:8000/ready}
REDIS_URL=${REDIS_URL:-redis://localhost:6379}
DATABASE_URL=${DATABASE_URL:-postgresql://user:pass@localhost:5432/botcamp}
AI_HEALTH=${AI_HEALTH:-https://example.com/ai/health}

alert() {
  /bin/bash ./deployment/alert.sh "$1" || true
}

# /ready
if ! curl -fsS "$HEALTH_URL" -m 5 >/dev/null; then
  alert "CRITICAL: /ready failed at $(date -Iseconds)"
  systemctl restart botcamp.service || true
  sleep 10
  if ! curl -fsS "$HEALTH_URL" -m 5 >/dev/null; then
    alert "CRITICAL: /ready still failing after restart"
    exit 2
  else
    alert "Auto-heal: /ready recovered after restart"
  fi
fi

# Redis
python - <<'PY'
import os, sys, redis
try:
    r=redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
except Exception as e:
    print('REDIS_FAIL', e)
    sys.exit(1)
print('REDIS_OK')
PY
if [ $? -ne 0 ]; then
  alert "WARN: Redis ping failed. Attempting restart..."
  systemctl restart redis || true
  sleep 5
  python - <<'PY'
import os, sys, redis
try:
    r=redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
except Exception as e:
    print('REDIS_FAIL', e)
    sys.exit(1)
print('REDIS_OK')
PY
  if [ $? -ne 0 ]; then
    alert "CRITICAL: Redis still failing"
    exit 3
  fi
fi

# AI provider
if ! curl -fsS "$AI_HEALTH" -m 10 >/dev/null; then
  alert "WARN: AI provider unreachable. Switching to fallback."
  python - <<'PY'
import os, redis
r=redis.from_url(os.getenv('REDIS_URL'))
r.set('ai:active_provider','fallback',ex=3600)
print('fallback_set')
PY
fi

exit 0

