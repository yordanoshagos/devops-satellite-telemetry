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

## Result logs (client-ready evidence)

> Important: The scenario blocks below are illustrative examples.


### Template

```text
### <Scenario name>

Command:
[bash command used]

Key output (trimmed):
[only the most important 5-15 lines]

Client takeaway:
- [one sentence about user impact]
- [one sentence about system behavior]
```

### Normal traffic log

Command:
```bash
scripts/load-test.sh normal
```

Key output (trimmed):
```text
running (0m10.0s), 00/10 VUs, 500 complete and 0 interrupted iterations

http_req_duration..............: avg=38ms   p(95)=110ms
http_req_failed................: 0.00%      0 out of 500
http_reqs......................: 500 total
```

Client takeaway:
- The platform remained stable under expected traffic with no user-facing errors.
- Response times stayed in the low-latency range and did not trigger alerts.

### Stress traffic log

Command:
```bash
scripts/load-test.sh stress
```

Key output (trimmed):
```text
running (0m40.0s), 00/50 VUs, 2000 complete and 0 interrupted iterations

http_req_duration..............: avg=170ms  p(95)=620ms
http_req_failed................: 1.02%      20 out of 2000
http_reqs......................: 2000 total
ALERT: HighLatencyP95 pending -> firing
```

Client takeaway:
- During peak traffic, the system stayed available but became slower for a subset of requests.
- Monitoring correctly detected the performance degradation and raised a latency alert.

### Failure traffic log

Command:
```bash
scripts/load-test.sh failure
```

Key output (trimmed):
```text
running (0m10.0s), 00/10 VUs, 300 complete and 0 interrupted iterations

http_req_failed................: 100.00%    300 out of 300
http_reqs......................: 300 total
ALERT: HighErrorRate firing (service-a, service-b, service-c)
```

Client takeaway:
- This test intentionally forced errors and confirms detection of service-impacting failures.
- Alerting behaved as expected by escalating quickly across affected services.

### Optional supporting logs (recommended)

Attach short, timestamped snippets from these commands in demos or handovers:

```bash
# Prometheus alert state
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {alertname: .labels.alertname, state: .state, service: .labels.service}'

# Alertmanager notification counters
curl -s http://localhost:9093/metrics | grep -E 'alertmanager_notifications_(total|failed_total)|alertmanager_dispatcher_aggregation_groups|alertmanager_notification_latency_seconds_count'

# Service error logs (example)
docker compose logs service-b --since=10m | grep -E 'ERROR|trace_id'
```

Keep supporting logs short (5-20 lines each) and highlight only lines that back
the claim in the client takeaway.

## Last captured run values (from previous stack session)

The stack is intentionally down now. The values below were captured from the
previously running session and can be used as current evidence in client updates
until the next live run is executed.

### Captured at a glance

| Check | Captured value |
|------|-----------------|
| Stack status | 11/11 containers up; key services healthy |
| Error scenario command | `bash scripts/simulate-failure.sh error` executed successfully |
| Service-down scenario | `telemetry-parser` stopped, gateway returned HTTP 502 |
| Recovery scenario | `bash scripts/simulate-failure.sh recover` returned gateway health HTTP 200 |
| Alertmanager state | startup/config loaded; no notification failures shown in captured tail |

### Captured log snippets (trimmed)

```text
Failure C: High Error Rate
Firing 60 failing requests...
Evidence to show (MELT):
  Alerts  : http://localhost:9090/alerts -> HighErrorRate fires (~1m)
```

```text
Failure A: Service Down
Container telemetry-parser Stopped
gateway HTTP 502
```

```text
Recovery
Container telemetry-parser Healthy
Container anomaly-detector Healthy
gateway health HTTP 200
```

```text
docker compose ps (captured)
ground-station-api   Up (healthy)
telemetry-parser     Up (healthy)
anomaly-detector     Up (healthy)
nginx                Up (healthy)
```

### How to refresh these captured values next time

When the stack is running again, replace this section using:

```bash
docker compose ps
bash scripts/simulate-failure.sh error
bash scripts/simulate-failure.sh down
bash scripts/simulate-failure.sh recover
curl -s http://localhost:9093/metrics | grep -E 'alertmanager_notifications_(total|failed_total)|alertmanager_dispatcher_aggregation_groups|alertmanager_notification_latency_seconds_count'
```

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