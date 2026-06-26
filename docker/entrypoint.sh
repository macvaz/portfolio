#!/bin/sh
set -e

case "$1" in
  api)
    exec uvicorn portfolio.api.api:app --host 0.0.0.0 --port 8000
    ;;
  job)
    exec python job.py
    ;;
  *)
    exec "$@"
    ;;
esac
