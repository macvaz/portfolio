#!/usr/bin/env bash
# Download Morningstar category monthly averages inside the portfolio container.
#
# If MORNINGSTAR_ACCESS_TOKEN is unset, fetch one via the Playwright helper.
#
# Usage:
#   ./bin/categories_batch.sh
#   ./bin/categories_batch.sh --limit 3
#   MORNINGSTAR_ACCESS_TOKEN='…' ./bin/categories_batch.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${PORTFOLIO_CONTAINER:-portfolio}"
IMAGE="${MORNINGSTAR_PLAYWRIGHT_IMAGE:-portfolio-playwright}"

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -qx true; then
  echo "Container '$CONTAINER' is not running." >&2
  echo "Start it with: docker compose -f docker/docker-compose.yml up -d" >&2
  exit 1
fi

if [[ -z "${MORNINGSTAR_ACCESS_TOKEN:-}" ]]; then
  echo "Fetching Morningstar access token via Playwright…" >&2
  if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    docker build -f "${ROOT}/docker/playwright/Dockerfile" -t "${IMAGE}" \
      "${ROOT}/docker/playwright" >/dev/null
  fi
  MORNINGSTAR_ACCESS_TOKEN="$(
    docker run --rm --init --ipc=host "$IMAGE"
  )"
  if [[ -z "${MORNINGSTAR_ACCESS_TOKEN}" ]]; then
    echo "Failed to obtain Morningstar access token." >&2
    exit 1
  fi
  export MORNINGSTAR_ACCESS_TOKEN
  echo "Token acquired (${#MORNINGSTAR_ACCESS_TOKEN} chars)." >&2
fi

exec docker exec -i \
  -e "MORNINGSTAR_ACCESS_TOKEN=${MORNINGSTAR_ACCESS_TOKEN}" \
  "$CONTAINER" python -m portfolio.batch.categories "$@"
