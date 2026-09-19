#!/usr/bin/env bash
# Build/run the Playwright helper that prints a Morningstar access_token.
#
# Usage:
#   ./bin/morningstar_token.sh
#   ./bin/morningstar_token.sh --url 'https://global.morningstar.com/…'
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${MORNINGSTAR_PLAYWRIGHT_IMAGE:-portfolio-playwright}"

docker build -f "${ROOT}/docker/playwright/Dockerfile" -t "${IMAGE}" \
  "${ROOT}/docker/playwright" >/dev/null

exec docker run --rm --init --ipc=host "${IMAGE}" "$@"
