#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
JWT_TOKEN="${JWT_TOKEN:-}"
IMAGE_PATH="${IMAGE_PATH:-}"
SCAN_TYPE="${SCAN_TYPE:-RECEIPT}"

if [[ -z "$JWT_TOKEN" ]]; then
  echo "JWT_TOKEN is required (use a real Spring Boot access token)"
  exit 1
fi

if [[ -z "$IMAGE_PATH" ]]; then
  echo "IMAGE_PATH is required (absolute or relative path to image)"
  exit 1
fi

if [[ ! -f "$IMAGE_PATH" ]]; then
  echo "Image not found: $IMAGE_PATH"
  exit 1
fi

echo "Running smoke test against $API_URL/api/v1/receipt/extract"

curl --fail-with-body -sS \
  -X POST "$API_URL/api/v1/receipt/extract" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -F "image=@$IMAGE_PATH" \
  -F "scanType=$SCAN_TYPE"

echo
echo "Smoke test completed"
