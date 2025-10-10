#!/usr/bin/env bash
set -euo pipefail

IMG_TAG="${1:-}"
if [[ -z "$IMG_TAG" ]]; then
  echo "Usage: $0 <image-tag-or-version>" >&2
  exit 1
fi

echo "Rollback to image: $IMG_TAG (implement provider CLI here)"
# Example for Fly.io (placeholder):
# fly deploy --image "$IMG_TAG" --remote-only

exit 0

