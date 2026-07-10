# Jaeger — Distributed Tracing

Jaeger shows the **journey of a single request** across `ground-station-api`
(A) → `telemetry-parser` (B) → `anomaly-detector` (C) → callback to A. Where
Prometheus tells you *that* latency or errors increased, Jaeger tells you
*where* in the request path it happened.

## How it is wired

- Each service runs **OpenTelemetry** auto-instrumentation
  (`opentelemetry-instrumentation-flask` + `-requests`) configured in each
  `service-*/app.py`.
- Incoming HTTP requests create a **server span**; outgoing `requests` calls to
  the next service create a **client span** and inject the W3C `traceparent`
  header, so the whole A→B→C→A chain is stitched into one trace.
- Spans are exported over **OTLP/gRPC** to `jaeger:4317`
  (`OTEL_EXPORTER_OTLP_ENDPOINT`, set in `docker-compose.yml`).
- Jaeger all-in-one is started with `COLLECTOR_OTLP_ENABLED=true` and serves its
  UI on **http://localhost:16686**.

Each span carries: service name, endpoint/route, duration, status code, and
error state (failed spans are flagged red in the UI).

## Trace demo (matches the PRD)

1. Send a successful request through the gateway:
   ```bash
   curl -X POST http://localhost/telemetry \
     -H "Content-Type: application/json" \
     -d '{"satellite_id":"SAT-001","mission_id":"MISSION-ALPHA-7","timestamp":"2026-06-18T09:30:00Z","telemetry_frame":{"battery_voltage":14.2,"solar_panel_temp":45.3,"gyro_x":0.01,"gyro_y":-0.02,"gyro_z":0.0,"signal_strength_dbm":-85,"downlink_frequency":437.5}}'
   ```
2. Open Jaeger at http://localhost:16686
3. In **Service**, pick `ground-station-api` and click **Find Traces**.
4. Open the trace and confirm the full journey:
   `ground-station-api → telemetry-parser → anomaly-detector` (+ the callback
   span back into `ground-station-api`).
5. Trigger a slow or failing request:
   ```bash
   curl http://localhost/slow    # latency injected in A, B and C
   curl -i http://localhost/fail # 500 propagated through A → B → C
   ```
6. Reopen the trace: for `/slow` the long span shows **where** the latency is;
   for `/fail` the red span shows **which** service failed.

## Correlating traces with logs

Every structured log line emitted during a request includes the `trace_id`
(see `service-*/app.py` log formatter). Copy a `trace_id` from the logs
(`docker compose logs ground-station-api`) and paste it into Jaeger's
**Search → Trace ID** box, or click the derived **TraceID** link from a Loki log
line inside Grafana.
