#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${HOLDINGS_MONITOR_PROJECT_ROOT:?HOLDINGS_MONITOR_PROJECT_ROOT is required}"
PYTHON_BIN="${HOLDINGS_MONITOR_PYTHON_BIN:-python}"
PROFILE_PATH="${HOLDINGS_MONITOR_PROFILE:?HOLDINGS_MONITOR_PROFILE is required}"
LOCK_FILE="${HOLDINGS_MONITOR_LOCK_FILE:-/tmp/holdings-monitor.lock}"
MAX_DELAY_SECONDS="${HOLDINGS_MONITOR_RANDOM_DELAY_MAX_SECONDS:-5400}"
LOG_FILE="${HOLDINGS_MONITOR_RUNNER_LOG_FILE:-$PROJECT_ROOT/logs/systemd-monitor.log}"

mkdir -p "$PROJECT_ROOT/logs"

if [[ -f "$PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "$(date '+%F %T') [skip] another run is still active" >> "$LOG_FILE"
  exit 0
fi

cd "$PROJECT_ROOT"
export PYTHONNOUSERSITE="${PYTHONNOUSERSITE:-1}"

DELAY=$((RANDOM % MAX_DELAY_SECONDS))
echo "$(date '+%F %T') [start] sleeping ${DELAY}s before monitor run" >> "$LOG_FILE"
sleep "$DELAY"

echo "$(date '+%F %T') [run] starting monitor" >> "$LOG_FILE"
"$PYTHON_BIN" -m holdings_monitor.cli run >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [[ "$EXIT_CODE" -eq 0 ]]; then
  echo "$(date '+%F %T') [done] monitor finished successfully" >> "$LOG_FILE"
else
  echo "$(date '+%F %T') [fail] monitor exited with code $EXIT_CODE" >> "$LOG_FILE"
fi

exit "$EXIT_CODE"
