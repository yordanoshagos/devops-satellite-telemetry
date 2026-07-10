#!/usr/bin/env bash
# =============================================================================
# load-test.sh - repeatable load test wrapper for the MELT stack.
#
# Prefers k6 (scripts/load-test.js). If k6 is not installed, falls back to a
# simple curl-based generator so a reviewer can still drive traffic.
#
# Usage:
#   scripts/load-test.sh normal    # baseline (default)
#   scripts/load-test.sh stress    # high concurrency
#   scripts/load-test.sh failure   # hammer /fail to trip the error alert
#
# Env:
#   BASE_URL   target gateway (default http://localhost)
# =============================================================================
set -euo pipefail

SCENARIO="${1:-normal}"
BASE_URL="${BASE_URL:-http://localhost}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Load test: scenario=${SCENARIO} target=${BASE_URL} =="

if command -v k6 >/dev/null 2>&1; then
  exec k6 run -e "SCENARIO=${SCENARIO}" -e "BASE_URL=${BASE_URL}" "${SCRIPT_DIR}/load-test.js"
fi

echo "k6 not found -> using curl fallback (install k6 for full metrics)."

case "${SCENARIO}" in
  normal)  REQUESTS=500;  CONCURRENCY=10; MODE=telemetry ;;
  stress)  REQUESTS=2000; CONCURRENCY=50; MODE=telemetry ;;
  failure) REQUESTS=300;  CONCURRENCY=10; MODE=fail ;;
  *) echo "Unknown scenario: ${SCENARIO}" >&2; exit 2 ;;
esac

PAYLOAD='{"satellite_id":"SAT-001","mission_id":"MISSION-ALPHA-7","timestamp":"2026-06-18T09:30:00Z","telemetry_frame":{"battery_voltage":14.2,"solar_panel_temp":45.3,"gyro_x":0.01,"gyro_y":-0.02,"gyro_z":0.0,"signal_strength_dbm":-85,"downlink_frequency":437.5}}'

one_request() {
  if [ "${MODE}" = "fail" ]; then
    curl -s -o /dev/null -w "%{http_code}\n" "${BASE_URL}/fail"
  else
    curl -s -o /dev/null -w "%{http_code}\n" -X POST "${BASE_URL}/telemetry" \
      -H "Content-Type: application/json" -d "${PAYLOAD}"
  fi
}
export -f one_request
export BASE_URL MODE PAYLOAD

START=$(date +%s)
seq "${REQUESTS}" | xargs -P "${CONCURRENCY}" -I{} bash -c 'one_request' >/tmp/loadtest_codes.txt
END=$(date +%s)

echo "Completed ${REQUESTS} requests in $((END - START))s"
echo "Status code distribution:"
sort /tmp/loadtest_codes.txt | uniq -c | sort -rn