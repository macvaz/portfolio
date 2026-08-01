#!/usr/bin/env bash
LOG_FILE="$LOGS_DIR/portfolio.log"

set +e
docker exec -t portfolio python batch.py >"$LOG_FILE" 2>&1
EXIT_CODE=$?
set -e

if [ "$EXIT_CODE" -ne 0 ] || grep -qiE 'Traceback|DownloadError|Error:|failed' "$LOG_FILE"; then
  echo "Portfolio batch reported an error (exit=$EXIT_CODE); sending email to $MAILTO"
  mutt -s "Portfolio batch failed" -a "$LOG_FILE" -- "$MAILTO" <"$LOG_FILE"
  exit 1
fi

echo "Portfolio batch completed successfully"