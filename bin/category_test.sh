#!/usr/bin/env bash
# Run Morningstar category_test.py inside the portfolio container.
# Optional: export MORNINGSTAR_ACCESS_TOKEN for live SAL category charts.
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

exec docker "${exec_args[@]}" "$CONTAINER" python category_test.py "$@"