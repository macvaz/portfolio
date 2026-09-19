#!/usr/bin/env bash
set -euo pipefail

BASEDIR=$(dirname "$0")
# shellcheck source=/dev/null
source "$BASEDIR/.env"

LOG_FILE="$LOGS_DIR/category.log"

set +e

# Download the morningstar token
docker run \
  --rm --ipc=host \
  -e MS_BEARER_TOKEN_PATH=/data/morningstar.token \
  -v /tmp:/data \
  headless-browser

docker exec portfolio python category.py >"$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -ne 0 ] || grep -qiE 'Traceback|DownloadError|Error:|failed' "$LOG_FILE"; then
  echo "Portfolio category reported an error (exit=$EXIT_CODE); sending email to $MAILTO"
  mutt -s "Portfolio category failed" -a "$LOG_FILE" -- "$MAILTO" <"$LOG_FILE"
  exit 1
fi

echo "Portfolio category completed successfully"
