#!/usr/bin/env bash
set -euo pipefail

BASEDIR=$(dirname "$0")
# shellcheck source=/dev/null
source "$BASEDIR/.env"

LOG_FILE="$LOGS_DIR/portfolio.log"

set +e
docker exec portfolio python batch.py >"$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -ne 0 ] || grep -qiE 'Traceback|DownloadError|Error:|failed' "$LOG_FILE"; then
  # stderr reaches cron (MAILTO); mutt also sends the log attachment
  echo "Portfolio batch reported an error (exit=$EXIT_CODE); sending email to $MAILTO" >&2
  mutt -s "Portfolio batch failed" -a "$LOG_FILE" -- "$MAILTO" <"$LOG_FILE"
  exit 1
fi
