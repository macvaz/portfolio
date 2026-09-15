#!/usr/bin/env bash
# Download Morningstar category monthly averages inside the portfolio container.
# Usage:
#   export MORNINGSTAR_ACCESS_TOKEN='…'
#   ./bin/categories_batch.sh
#   ./bin/categories_batch.sh --limit 3
set -euo pipefail

CONTAINER="${PORTFOLIO_CONTAINER:-portfolio}"

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -qx true; then
  echo "Container '$CONTAINER' is not running." >&2
  echo "Start it with: docker compose -f docker/docker-compose.yml up -d" >&2
  exit 1
fi

exec_args=(exec -i)
if [[ -n "${MORNINGSTAR_ACCESS_TOKEN:-}" ]]; then
  exec_args+=(-e "MORNINGSTAR_ACCESS_TOKEN=${MORNINGSTAR_ACCESS_TOKEN}")
fi

exec docker "${exec_args[@]}" "$CONTAINER" python -m portfolio.batch.categories "$@"
