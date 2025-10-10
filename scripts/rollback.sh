#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <image-tag>" >&2
  exit 1
fi

tag="$1"
echo "Rollback to image tag: $tag"
echo "Implement provider-specific rollback here (Render/Fly/Railway)."


