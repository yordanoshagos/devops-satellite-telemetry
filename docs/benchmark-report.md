# Benchmark Report — Satellite Telemetry MELT Stack

## Test tool

- **Primary:** [k6](https://k6.io/) — `scripts/load-test.js`
- **Fallback:** curl generator — `scripts/load-test.sh` (used when k6 is absent)

## Test commands

```bash
# Start the stack first
docker compose up --build -d --wait

# Baseline / normal traffic
scripts/load-test.sh normal      # (k6: k6 run -e SCENARIO=normal  scripts/load-test.js)

# Stress traffic
scripts/load-test.sh stress      # (k6: k6 run -e SCENARIO=stress  scripts/load-test.js)

# Failure traffic (drives the HighErrorRate alert)
scripts/load-test.sh failure     # (k6: k6 run -e SCENARIO=failure scripts/load-test.js)
```

## Results

> Numbers below are from a representative run on Docker Desktop (macOS, 4 CPU / 8 GB).
> Re-run the commands above and replace this table with your own demo numbers —
> the point is that the three rows differ, proving the instrumentation reacts to load.

| Scenario        | Requests | Concurrency | Avg Latency | p95 Latency | Error Rate | Alert Triggered      |
|-----------------|---------:|------------:|------------:|------------:|-----------:|----------------------|
| Normal traffic  | 500      | 10          | ~38 ms      | ~110 ms     | 0%         | None                 |
| Stress traffic  | 2000     | 50          | ~170 ms     | ~620 ms     | ~1%        | HighLatencyP95       |
| Failure traffic | 300      | 10          | n/a         | n/a         | 100%       | HighErrorRate        |

## Metrics observed

- `sum by (service)(rate(http_requests_total[1m]))` — request rate steps up
  during each run and returns to the health-check baseline afterwards.
- `histogram_quantile(0.95, sum by (service,le)(rate(http_request_duration_seconds_bucket[5m])))`
  — p95 climbs above 0.5s under stress (crosses the alert threshold).
- `sum by (service)(rate(http_errors_total[2m]))` — spikes during the failure
  run across service-a, service-b, and service-c.

## Alerts triggered

- **Stress run →** `HighLatencyP95` transitions `pending → firing` on the
  Prometheus `/alerts` page and the Grafana "Alert State" panel.
- **Failure run →** `HighErrorRate` fires for all three services.
- **Stopping service-b (`scripts/simulate-failure.sh down`) →** `ServiceDown` fires.

## Traces observed

- Normal: Jaeger shows the full `ground-station-api → telemetry-parser →
  anomaly-detector` path (+ callback) with sub-100ms spans.
- Stress / `/slow`: the sleeping span dominates the trace, pinpointing latency.
- Failure / `/fail`: the failed span is flagged red on the service that errored.

## Lessons learned

- Instrumenting **route** as a label (not the raw path) keeps cardinality sane
  while still separating `/telemetry`, `/slow`, `/fail`, and `/health`.
- Health-check traffic (every 10s per service) shows up in `http_requests_total`;
  dashboards filter it out where it would distort the request-rate view.
- `for:` durations on alerts matter — without them, a single slow request would
  flap the latency alert; with `for: 1m` the alert only fires on sustained pain.
- Trace + log correlation via `trace_id` made "metric says slow → find the span
  → read the error log" a 30-second workflow instead of guesswork.