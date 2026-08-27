# Reliability Target

**Owners:** Yordanos (Service A) + Arsema (Platform)  
**Environment:** AWS account `240462142849`, region `eu-central-1`  
**Cluster:** `devops-g10-iac-cluster`  
**ALB:** `http://devops-g10-iac-alb-1207406256.eu-central-1.elb.amazonaws.com`  
**Measured:** 2026-08-28 (lab baseline after rehost)

---

## Critical user journey

**Name:** Satellite telemetry ingest (accept → analyze → complete)

**Happy path**

1. Client `POST /telemetry` to the internet-facing ALB  
2. ALB → `ground-station-api` (Service A, desired 2)  
3. A → `telemetry-parser` (Service B) via Service Connect (`telemetry-parser:3002`)  
4. B → `anomaly-detector` (Service C) via Service Connect (`anomaly-detector:3003`)  
5. C → A `POST /callback` (SG edge C→A on 3001)  
6. Client `GET /status/<processing_request_id>` shows completed analysis

This is the journey we protect with SLIs/SLOs below.

---

## SLIs

| # | SLI | Definition | Primary signal |
|---|-----|------------|----------------|
| 1 | **Availability** | Fraction of `GET /health` via ALB that return HTTP 200 with `status=operational` and `telemetry_parser=reachable` | ALB → A `/health` |
| 2 | **Ingest latency** | Time from `POST /telemetry` accept (HTTP 202) until parser response is recorded on A (forward path A→B) | A logs `duration_ms` on `/telemetry`; target p95 |
| 3 | **Journey success** | Fraction of accepted telemetry requests that reach a terminal status (`completed` / analysis applied) rather than remaining `awaiting_callback` or disappearing across A tasks | `GET /status/<id>` + A/B/C logs |

---

## SLOs (30-day window)

| SLI | SLO | Error budget (30d) |
|-----|-----|--------------------|
| Availability | **99.5%** operational `/health` | ≈ **3.6 hours** non-operational |
| Ingest latency (p95) | **< 2.0s** for accept+forward (A→B) | Burn when p95 stays ≥ 2s |
| Journey success | **99.0%** reach terminal completed status | ≈ **1%** of accepted requests may fail/stick |

### Error-budget policy

| Budget state | Action |
|--------------|--------|
| **Healthy** (>50% remaining) | Normal feature work; scheduled deploys |
| **Burning** (25–50% remaining) | Freeze non-critical changes; pair on reliability fixes |
| **Exhausted** (<25% or open SEV) | Incident mode only; platform + service owners on fix path |

---

## Baseline evidence (captured 2026-08-28)

### ECS desired vs running

| Service | Desired | Running |
|---------|---------|---------|
| `ground-station-api` | 2 | 2 |
| `telemetry-parser` | 1 | 1 |
| `anomaly-detector` | 1 | 1 |

### `/health` (ALB)

```json
{
  "dependencies": {
    "anomaly_detector": "skipped: A→C denied by traffic contract",
    "telemetry_parser": "reachable"
  },
  "ground_station_id": "GS-Nairobi-1",
  "service": "ground-station-api",
  "service_version": "v1.0.0",
  "status": "operational"
}
```

C is intentionally not probed from A (traffic contract).

### `POST /telemetry` (sample)

- Request accepted: `processing_request_id=1578c224-3c92-4920-9c6b-80e24141e648`, `status=accepted`
- B logs: parse success + forward to detector
- B logs: `Detector responded: nominal` (A→B→C forward path OK)

### Known gap affecting journey-success SLI

`GET /status/<id>` remained `awaiting_callback` after A→B→C succeeded. Also observed intermittent `Request ID not found` on `/status` while A runs **2 tasks** with in-memory status — ALB can land status/callback on a different task than the one that accepted the request.

**Implication:** Availability SLI can be green while journey-success SLI burns. Tracked as a reliability condition in `GO-NO-GO.md` (platform/Arsema).

Raw command capture: `production-readiness/alerts/baseline-e2e.txt`.

---

## How we will keep measuring

| SLI | Lab method now | Stretch |
|-----|----------------|---------|
| Availability | Periodic `curl $ALB/health` + ECS running counts | ALB target health / CloudWatch |
| Ingest latency | A structured logs `duration_ms` on `/telemetry` | Prometheus histogram p95 (compose `alert-rules.yml` already has HighLatencyP95) |
| Journey success | Sample `POST /telemetry` + poll `/status` + confirm callback log on A | Shared store for status (fix sticky-session / in-memory gap) |

---

## Owners for ongoing review

| Role | Person | Responsibility |
|------|--------|----------------|
| Service A | Yordanos | `/health`, ALB face, ingest latency, status API behaviour |
| Platform | Arsema | Cluster/ALB/SG/Service Connect, error-budget calls, GO/NO-GO |
| Service B | Saloi | Parser availability (feeds availability + forward path) |
| Service C | Berissa | Analyze + callback completion (feeds journey success) |

---

## Service B review (Saloi, 2026-08-28)

Do these SLOs match what B can actually support?

| SLI | SLO | Saloi |
|-----|-----|-------|
| Availability 99.5% | Keep, with care | B **desired=1** — every replace is a full parse outage (~2 min observed). Exclude planned deploys from the budget or we burn it on routine SHA rolls. `/health` HTTP 200 is not enough; require `telemetry_parser=reachable`. |
| Ingest latency p95 < 2s | **OK for the B hop** | Day 0 `parse_complete` duration_ms≈0, B→C ~15ms. Do not use accept→completed until callback works. |
| Journey success 99% | **Cannot support today** | 0% `completed` on Day 0. C cannot resolve `ground-station-api` (see failure-map Break 5). Even after DNS, A in-memory store + desired=2 makes ALB `/status` untrustworthy. Use log-based success (B `parse_complete` + C `analyze_complete`) until then. |
