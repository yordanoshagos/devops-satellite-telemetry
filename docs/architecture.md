# Architecture — Satellite Telemetry MELT Operating Layer

This document describes the service architecture and the MELT telemetry flow
(Metrics, Events, Logs, Traces) added in the observability lab.

## 1. Service architecture

```
                 Client / Load test (k6)
                          |
                          v
                +-------------------+
                |   Nginx (:80)     |  public gateway
                +-------------------+
                          |
                          v
        +-------------------------------------+
        |  service-a  ground-station-api :3001|  public entry point
        +-------------------------------------+
                          |  POST /parse
                          v
        +-------------------------------------+
        |  service-b  telemetry-parser   :3002|  internal
        +-------------------------------------+
                          |  POST /analyze
                          v
        +-------------------------------------+
        |  service-c  anomaly-detector   :3003|  internal
        +-------------------------------------+
                          |  POST /callback
                          +-----------------> back to service-a

Networks:
  frontend       : nginx, service-a
  backend (internal, no internet): service-a, service-b, service-c,
                   prometheus, jaeger
  observability  : prometheus, grafana, loki, promtail, alertmanager,
                   cadvisor, jaeger
```

Only Nginx publishes a port to the outside on the app side. Services B and C
live on the `internal: true` backend network and cannot be reached from the host.

## 2. Request flow (happy path)

1. Client `POST /telemetry` → Nginx → service-a.
2. service-a assigns/propagates `X-Request-ID` (== `processing_request_id`) and
   forwards the frame to service-b `/parse`.
3. service-b validates the checksum, parses the frame, forwards to service-c
   `/analyze`.
4. service-c checks mission thresholds and `POST /callback`s the result back to
   service-a.
5. Client receives `202 accepted` with the `processing_request_id`.

## 3. Telemetry flow (MELT)

```
 service-a/b/c ──/metrics──▶ Prometheus ──▶ Grafana (dashboards + alert state)
      │                          │
      │                          └──▶ Alertmanager (routing)
      │
      ├── stdout JSON logs ──▶ Promtail ──▶ Loki ──▶ Grafana (Logs panel)
      │
      └── OTLP spans ──▶ Jaeger ──▶ Jaeger UI / Grafana Jaeger datasource
```

| Signal  | Source                                   | Stored / viewed in            |
|---------|------------------------------------------|-------------------------------|
| Metrics | `prometheus_client` on each service      | Prometheus → Grafana          |
| Events  | Structured log events + README/benchmark | Loki / Grafana annotations    |
| Logs    | JSON logs on stdout (`request_id`,`trace_id`) | Promtail → Loki → Grafana |
| Traces  | OpenTelemetry (Flask + requests)         | Jaeger                        |

### 3a. Metrics collection flow

Each service exposes `/metrics` with:

- `http_requests_total{service,method,route,status_code}` — traffic
- `http_request_duration_seconds{service,method,route}` (histogram) — latency
- `http_errors_total{service,method,route,status_code}` — 5xx errors
- `service_up{service}` — process liveness

Prometheus scrapes each service by its **compose service name**
(`ground-station-api:3001`, `telemetry-parser:3002`, `anomaly-detector:3003`)
every 15s and stores data in the `prometheus-data` named volume. `cadvisor`
adds per-container CPU/memory/network metrics.

### 3b. Tracing flow

OpenTelemetry creates a server span per incoming request and a client span per
outgoing `requests` call, propagating W3C `traceparent` headers so a single
request becomes one trace spanning A → B → C → A(callback). Spans export via
OTLP/gRPC to `jaeger:4317`. See [`jaeger/README.md`](../jaeger/README.md).

### 3c. Logging flow

Every service logs one JSON object per line to stdout, including `service`,
`level`, `event`, `duration_ms`, `request_id` (== `processing_request_id`) and,
when a span is active, `trace_id`. Promtail tails container stdout via the
Docker socket, parses the JSON, and pushes to Loki; Grafana's Logs panel and a
derived field turn a `trace_id` into a clickable link to the Jaeger trace.

### 3d. Alerting flow

Prometheus evaluates [`alert-rules.yml`](../alert-rules.yml) every 15s:

- **ServiceDown** — `up{job=~"service-.*"} == 0` for 30s
- **HighErrorRate** — `sum by (service)(rate(http_errors_total[2m])) > 0.1` for 1m
- **HighLatencyP95** — `histogram_quantile(0.95, …rate(http_request_duration_seconds_bucket[5m])) > 0.5` for 1m

Firing alerts are visible on Prometheus `/alerts`, in the Grafana "Alert State"
panel, and are routed to Alertmanager (`:9093`).

## 4. Operational events

At least three meaningful events are represented as structured log entries
and/or observable state changes:

1. **Service startup** — `event=service_startup` log line per service on boot.
2. **Load test started/completed** — recorded in `docs/benchmark-report.md` and
   visible as a request-rate step change in Grafana.
3. **Failure triggered** — `event=lab_fail` / `event=lab_slow` log lines, plus
   the corresponding alert transitioning to `firing`.

## 5. Known limitations

- Jaeger all-in-one keeps traces **in memory** — restarting Jaeger loses them.
- Loki/Prometheus retention is lab-sized (local filesystem/volume); not tuned
  for production scale.
- `/slow` and `/fail` are **lab-only** endpoints and must never be shipped to a
  real deployment.
- Grafana uses default `admin/admin` credentials for the lab.
- `cadvisor` host metrics are richest on Linux; on Docker Desktop (macOS) some
  host-level series are limited.
