#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BOT_TOKEN:-}" || -z "${SUPER_ADMIN_CHAT_ID:-}" ]]; then
  echo "BOT_TOKEN and SUPER_ADMIN_CHAT_ID must be set" >&2
  exit 1
fi

MSG="${1:-Deployment alert}"
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d chat_id="${SUPER_ADMIN_CHAT_ID}" \
  -d parse_mode="Markdown" \
  -d text="$MSG" >/dev/null
echo "Alert sent"

