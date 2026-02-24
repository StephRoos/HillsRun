#!/bin/bash
#
# HillsRun Health Monitor
# Checks /health endpoint periodically and logs failures.
#
# Usage:
#   ./scripts/monitor.sh [API_URL]
#
# Cron example (run every minute):
#   * * * * * /path/to/HillsRun/scripts/monitor.sh https://api.hillsrun.com
#
# Log file: /tmp/hillsrun-monitor.log
# Failures are logged with timestamp. Successful checks are silent.
#

set -euo pipefail

API_URL="${1:-${GARMIN_API_URL:-https://api.hillsrun.com}}"
HEALTH_URL="${API_URL}/health"
LOG_FILE="/tmp/hillsrun-monitor.log"
CHECK_INTERVAL=60  # seconds between checks when running in loop mode

log_failure() {
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[${ts}] FAIL  ${HEALTH_URL}  →  $*" | tee -a "${LOG_FILE}"
}

log_recovery() {
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[${ts}] OK    ${HEALTH_URL}  →  recovered" | tee -a "${LOG_FILE}"
}

check_once() {
  local http_code
  local body

  body=$(curl -s -w "\n%{http_code}" --max-time 10 "${HEALTH_URL}" 2>/dev/null || echo -e "\n000")
  http_code=$(echo "${body}" | tail -n1)
  local response
  response=$(echo "${body}" | sed '$d')

  if [[ "${http_code}" != "200" ]]; then
    log_failure "HTTP ${http_code}"
    return 1
  fi

  local status
  status=$(echo "${response}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', '?'))" 2>/dev/null || echo "?")

  if [[ "${status}" != "ok" ]]; then
    log_failure "status=${status}  body=${response}"
    return 1
  fi

  return 0
}

# ---------------------------------------------------------------------------
# Single check mode (for cron — runs once and exits)
# ---------------------------------------------------------------------------
if [[ "${2:-}" == "--once" ]] || [[ -t 0 && "${2:-}" == "" ]]; then
  # Detect cron context: if stdin is not a terminal, run once
  if ! tty -s 2>/dev/null; then
    # Running from cron
    PREV_FAILED=0
    if [[ -f "${LOG_FILE}" ]] && tail -1 "${LOG_FILE}" 2>/dev/null | grep -q "^.*FAIL"; then
      PREV_FAILED=1
    fi

    if check_once; then
      if [[ "${PREV_FAILED}" -eq 1 ]]; then
        log_recovery
      fi
    fi
    exit 0
  fi
fi

# ---------------------------------------------------------------------------
# Interactive loop mode (runs continuously when launched from terminal)
# ---------------------------------------------------------------------------
echo "HillsRun Monitor — checking ${HEALTH_URL} every ${CHECK_INTERVAL}s"
echo "Log file: ${LOG_FILE}"
echo "Press Ctrl+C to stop"
echo ""

LAST_STATUS="ok"

while true; do
  if check_once; then
    if [[ "${LAST_STATUS}" != "ok" ]]; then
      log_recovery
      LAST_STATUS="ok"
    fi
  else
    LAST_STATUS="fail"
  fi
  sleep "${CHECK_INTERVAL}"
done
