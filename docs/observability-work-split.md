# Observability Lab — Work Split & Collaboration Log

How the four of us divided the MELT observability work. This time the split is
**deliberately equal — nobody leads, nobody is a passenger** — and the
pipeline-touching files are authored by the two lighter contributors last week
(Saloi, Berissa) with the heavier two (Arsema, Yordanos) reviewing, so the
whole team can defend the pipeline before Saturday.

## Balanced ownership (author) + reviewer

| Member | Authors | Reviewed by |
|--------|---------|-------------|
| **Yordanos** | Service A instrumentation + tracing docs | Saloi |
| **Saloi** | Service B instrumentation + Prometheus/alerts + **CI workflow** | Arsema |
| **Berissa** | Service C instrumentation + load/failure tooling + **prod compose** | Yordanos |
| **Arsema** | Compose + Grafana + logs pipeline + README | Berissa |

Review cycle: Yordanos → Saloi → Arsema → Berissa → Yordanos (everyone reviews
exactly one PR and is reviewed by exactly one). The pipeline files (CI workflow,
prod compose) are owned by Saloi and Berissa on purpose.

Shared decision made together up front: metric names/labels
(`http_requests_total`, `http_request_duration_seconds`, `http_errors_total`,
`service_up` with `service/method/route/status_code` labels) so Prometheus, the
alerts, and the Grafana dashboard all line up. The `/slow` and `/fail` lab
endpoints were designed as a **chain** (A→B→C) so one request produces a useful
multi-service trace.

## Files per person

### Yordanos — Service A + tracing docs (reviewed by Saloi)
- `service-a/app.py` — Prometheus middleware + OpenTelemetry bootstrap + `/metrics`, `/slow`, `/fail`, `trace_id` in logs
- `service-a/requirements.txt` — prometheus-client + OpenTelemetry deps
- `service-a/tests/test_app.py` — `/metrics`, `/slow`, `/fail` tests
- `service-a/conftest.py` — disables tracer + zero sleep in unit tests
- `jaeger/README.md` — tracing deep-dive + trace demo
- `docs/architecture.md` — request + telemetry (MELT) flow

### Saloi — Service B + Prometheus/alerts + CI (reviewed by Arsema)
- `service-b/app.py` — same instrumentation; `/slow` `/fail` propagate to service-c
- `service-b/requirements.txt`
- `service-b/tests/test_app.py`, `service-b/conftest.py`
- `prometheus.yml` — scrape by compose service name, named volume, cAdvisor job
- `alert-rules.yml` — ServiceDown / HighErrorRate / HighLatencyP95 (fully documented)
- `.github/workflows/container-ci-cd.yml` — raise `--wait-timeout` to 180 for the observability services

### Berissa — Service C + load/failure + prod compose (reviewed by Yordanos)
- `service-c/app.py` — leaf instrumentation; `/slow` sleeps, `/fail` returns 500
- `service-c/requirements.txt`
- `service-c/tests/test_app.py`, `service-c/conftest.py`
- `scripts/load-test.js` — k6 (normal/stress/failure scenarios)
- `scripts/load-test.sh` — wrapper (k6 or curl fallback)
- `scripts/simulate-failure.sh` — trigger a failure + print MELT evidence
- `docs/benchmark-report.md` — scenarios + results
- `docker-compose.prod.yml` — observability stack for the published-image deploy

### Arsema — Compose + Grafana + logs pipeline + README (reviewed by Berissa)
- `docker-compose.yml` — jaeger/prometheus/grafana/alertmanager/loki/promtail/cadvisor, volumes, `observability` network, OTEL env on every service
- `grafana/provisioning/datasources/datasources.yml` — Prometheus + Loki + Jaeger (+ derived trace links)
- `grafana/provisioning/dashboards/dashboards.yml`
- `grafana/dashboards/melt-overview.json` — the MELT operating view
- `loki/loki-config.yml`, `promtail/promtail-config.yml`, `alertmanager/alertmanager.yml`
- `README.md` — Observability (MELT) Stack section
- `docs/observability-work-split.md` — this file

## Collaboration & debugging log

Real issues we hit bringing the stack up (kept here as evidence we debugged
together, not just wrote code):

1. **Loki crash-loop on boot.** Loki 3.1.1 rejected
   `limits_config.metric_aggregation_enabled` ("field not found"). Arsema owned
   the fix; Berissa confirmed logs started flowing afterwards
   (`loki_distributor_lines_received_total > 0`).
2. **Promtail "no such host: loki".** While Loki was crash-looping its DNS
   record disappeared, so Promtail's pushes retried. Once Loki was stable a
   `docker compose restart promtail` cleared the backlog.
3. **Loki not reachable from the host.** We deliberately do **not** publish
   Loki's `:3100`; Grafana reaches it over the internal network. We verify Loki
   from inside the `observability` network, not from the Mac host.
4. **Health-check noise in request-rate.** Every service's HEALTHCHECK hits
   `/health` every 10s, which showed up in `http_requests_total`. Saloi and
   Yordanos agreed to use the **route template** as the label and to filter
   `/health` in the dashboard rather than drop the metric.
5. **Tests importing app started the tracer.** OpenTelemetry made the test
   import try to reach Jaeger. Fix: a per-service `conftest.py` sets
   `OTEL_SDK_DISABLED=true` and `LAB_SLOW_SECONDS=0`. All 34 tests pass.

## Follow-up from last week's feedback

- **Branch protection:** enable "require 1 review before merge" on `develop`
  (GitHub → Settings → Branches) so the review cycle above is enforced, not just
  convention.
- **Spread pipeline knowledge:** Saloi authors the CI change and Berissa the
  prod-compose change; Arsema/Yordanos review — the lighter contributors defend
  pipeline changes out loud.

## Verification we ran

- `pytest` green for all three services (34 tests).
- `docker compose up -d` → all app services healthy.
- Prometheus `up` == 1 for service-a/b/c/prometheus/cadvisor.
- Jaeger shows a single trace spanning all three services (5 spans).
- Loki ingesting JSON logs with `service`, `level`, and `trace_id`.
- Grafana provisioned with 3 datasources + the MELT dashboard.
- `HighErrorRate` observed transitioning to **firing** after `scripts/simulate-failure.sh error`.
