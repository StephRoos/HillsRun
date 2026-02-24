#!/bin/bash
#
# HillsRun Post-Deploy Smoke Test
# Usage: ./scripts/smoke-test.sh [API_URL] [API_KEY]
#
# Runs a series of endpoint checks to verify the deployed API is healthy.
# Exits 0 if all tests pass, 1 if any test fails.
#
# Examples:
#   ./scripts/smoke-test.sh
#   ./scripts/smoke-test.sh https://api.hillsrun.com my-api-key
#

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_URL="${1:-${GARMIN_API_URL:-https://api.hillsrun.com}}"
API_KEY="${2:-${GARMIN_API_KEY:-}}"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
pass() {
  local label="$1"
  echo -e "  ${GREEN}PASS${RESET}  ${label}"
  PASS=$((PASS + 1))
}

fail() {
  local label="$1"
  local detail="${2:-}"
  echo -e "  ${RED}FAIL${RESET}  ${label}${detail:+  ($detail)}"
  FAIL=$((FAIL + 1))
}

check_status() {
  local label="$1"
  local url="$2"
  local expected_codes="$3"   # space-separated list, e.g. "200 204"
  shift 3
  local extra_args=("$@")

  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" "${extra_args[@]+"${extra_args[@]}"}" "${url}")

  for code in $expected_codes; do
    if [[ "${http_code}" == "${code}" ]]; then
      pass "${label} → HTTP ${http_code}"
      return
    fi
  done

  fail "${label}" "got HTTP ${http_code}, expected ${expected_codes}"
}

check_json_field() {
  local label="$1"
  local url="$2"
  local field="$3"
  local expected_value="$4"
  shift 4
  local extra_args=("$@")

  local body
  body=$(curl -s "${extra_args[@]+"${extra_args[@]}"}" "${url}")
  local actual
  actual=$(echo "${body}" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('${field}', ''))" 2>/dev/null || echo "")

  if [[ "${actual}" == "${expected_value}" ]]; then
    pass "${label} → ${field}=${actual}"
  else
    fail "${label}" "${field}=${actual}, expected ${expected_value}"
  fi
}

# ---------------------------------------------------------------------------
# Auth header helper
# ---------------------------------------------------------------------------
auth_args() {
  if [[ -n "${API_KEY}" ]]; then
    echo "-H" "X-API-Key: ${API_KEY}"
  fi
}

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}HillsRun Smoke Test${RESET}"
echo "  API: ${API_URL}"
echo "  Key: ${API_KEY:+(provided)}"
echo "  Key: ${API_KEY:-${RED}(not provided — auth endpoints will fail)${RESET}}"
echo ""

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# 1. Health endpoint — public, no auth required
echo "1. Health endpoint (public)"
check_status \
  "GET /health" \
  "${API_URL}/health" \
  "200"

check_json_field \
  "GET /health → status" \
  "${API_URL}/health" \
  "status" \
  "ok"

echo ""

# 2. Sync status — requires API key
echo "2. Sync status (authenticated)"
if [[ -n "${API_KEY}" ]]; then
  check_status \
    "GET /api/v1/sync/status" \
    "${API_URL}/api/v1/sync/status" \
    "200" \
    -H "X-API-Key: ${API_KEY}"
else
  echo -e "  ${YELLOW}SKIP${RESET}  GET /api/v1/sync/status (no API key)"
fi

echo ""

# 3. Daily summary — 200 or 204 (no data for that date range is ok)
echo "3. Daily summary (authenticated)"
if [[ -n "${API_KEY}" ]]; then
  check_status \
    "GET /api/v1/daily/summary?start_date=2026-01-01&end_date=2026-01-01" \
    "${API_URL}/api/v1/daily/summary?start_date=2026-01-01&end_date=2026-01-01" \
    "200 204" \
    -H "X-API-Key: ${API_KEY}"
else
  echo -e "  ${YELLOW}SKIP${RESET}  GET /api/v1/daily/summary (no API key)"
fi

echo ""

# 4. Activities list — 200
echo "4. Activities list (authenticated)"
if [[ -n "${API_KEY}" ]]; then
  check_status \
    "GET /api/v1/activities?limit=1" \
    "${API_URL}/api/v1/activities?limit=1" \
    "200" \
    -H "X-API-Key: ${API_KEY}"
else
  echo -e "  ${YELLOW}SKIP${RESET}  GET /api/v1/activities (no API key)"
fi

echo ""

# 5. Nutrition daily goal — 200 or 204
echo "5. Nutrition daily goal (authenticated)"
if [[ -n "${API_KEY}" ]]; then
  check_status \
    "GET /api/v1/nutrition/daily-goal" \
    "${API_URL}/api/v1/nutrition/daily-goal" \
    "200 204" \
    -H "X-API-Key: ${API_KEY}"
else
  echo -e "  ${YELLOW}SKIP${RESET}  GET /api/v1/nutrition/daily-goal (no API key)"
fi

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL=$((PASS + FAIL))
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "Results: ${GREEN}${PASS} passed${RESET} / ${RED}${FAIL} failed${RESET} / ${TOTAL} total"

if [[ "${FAIL}" -gt 0 ]]; then
  echo -e "${RED}Smoke test FAILED — check the output above${RESET}"
  exit 1
else
  echo -e "${GREEN}All smoke tests passed${RESET}"
  exit 0
fi
