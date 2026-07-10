#!/usr/bin/env bash
# =============================================================================
# simulate-failure.sh - trigger one controlled failure and print where to find
# the MELT evidence (Metrics / Events / Logs / Traces / Alerts).
#
# Usage:
#   scripts/simulate-failure.sh down     # Failure A: stop service-b (ServiceDown)
#   scripts/simulate-failure.sh slow     # Failure B: high latency  (HighLatencyP95)
#   scripts/simulate-failure.sh error    # Failure C: high error rate (HighErrorRate)
#   scripts/simulate-failure.sh recover  # restart everything and confirm healthy
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost}"
COMPOSE="${COMPOSE:-docker compose}"
ACTION="${1:-}"

banner() { echo; echo "==================== $* ===================="; }

case "${ACTION}" in
  down)
    banner "Failure A: Service Down (stopping telemetry-parser / service-b)"
    ${COMPOSE} stop telemetry-parser
    echo "Sending a request that now depends on a dead service:"
    curl -s -o /dev/null -w "  gateway HTTP %{http_code}\n" -X POST "${BASE_URL}/telemetry" \
      -H "Content-Type: application/json" \
      -d '{"satellite_id":"SAT-001","mission_id":"M","telemetry_frame":{"battery_voltage":14.2,"solar_panel_temp":45.3,"gyro_x":0,"gyro_y":0,"gyro_z":0,"signal_strength_dbm":-85,"downlink_frequency":437.5}}' || true
    cat <<'EOF'

Evidence to show (MELT):
  Metrics : Prometheus  http://localhost:9090/graph?g0.expr=up{job="service-b"}  -> 0
  Alerts  : http://localhost:9090/alerts -> ServiceDown becomes firing (~30s)
  Logs    : docker compose logs ground-station-api | grep -i unreachable
  Traces  : Jaeger http://localhost:16686 -> the trace shows the failed B hop
  Recover : scripts/simulate-failure.sh recover
EOF
    ;;

  slow)
    banner "Failure B: High Latency (GET /slow -> A -> B -> C all sleep)"
    echo "Firing 20 slow requests in the background (~ a minute of degraded p95)..."
    for _ in $(seq 20); do curl -s -o /dev/null "${BASE_URL}/slow" & done
    cat <<'EOF'

Evidence to show (MELT):
  Metrics : Grafana p95 Latency panel spikes; PromQL
            histogram_quantile(0.95, sum by (service,le)(rate(http_request_duration_seconds_bucket[5m])))
  Alerts  : http://localhost:9090/alerts -> HighLatencyP95 fires (~1m)
  Logs    : docker compose logs | grep lab_slow  (duration_ms is large)
  Traces  : Jaeger -> open a /slow trace, the sleeping span shows WHERE latency is
EOF
    ;;

  error)
    banner "Failure C: High Error Rate (GET /fail -> 500 across A, B, C)"
    echo "Firing 60 failing requests..."
    for _ in $(seq 60); do curl -s -o /dev/null "${BASE_URL}/fail" & done
    wait || true
    cat <<'EOF'

Evidence to show (MELT):
  Metrics : Grafana Error Rate panel; PromQL
            sum by (service)(rate(http_errors_total[2m]))
  Alerts  : http://localhost:9090/alerts -> HighErrorRate fires (~1m)
  Logs    : docker compose logs | grep -i '"level": "ERROR"'  (event=lab_fail)
  Traces  : Jaeger -> the /fail trace shows the red failed span in service-c
EOF
    ;;

  recover)
    banner "Recovery: restart services and confirm healthy"
    ${COMPOSE} start telemetry-parser anomaly-detector ground-station-api || true
    sleep 5
    curl -s -o /dev/null -w "gateway health HTTP %{http_code}\n" "${BASE_URL}/health" || true
    echo "Confirm up{job=~\"service-.*\"} == 1 in Prometheus and alerts return to green."
    ;;

  *)
    echo "Usage: $0 {down|slow|error|recover}" >&2
    exit 2
    ;;
esac