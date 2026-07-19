#!/bin/sh
set -e

# Containers need 0.0.0.0 so published ports are reachable.
# Local `python -m portfolio.api.api` defaults to 127.0.0.1 via PORTFOLIO_HOST.
HOST="${PORTFOLIO_HOST:-0.0.0.0}"
PORT="${PORTFOLIO_PORT:-8000}"

case "$1" in
  api)
    exec uvicorn portfolio.api.api:app --host "$HOST" --port "$PORT"
    ;;
  batch|job)
    exec python batch.py
    ;;
  *)
    exec "$@"
    ;;
esac
