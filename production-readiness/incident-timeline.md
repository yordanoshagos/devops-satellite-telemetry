# Incident Timeline — Service B down (ECS drill)

**Date:** 2026-08-28  
**Environment:** AWS `240462142849` / `eu-central-1` / `devops-g10-iac-cluster`  
**Incident lead:** Yordanos Tesfay Hagos (Service A)  
**Failure inject:** Saloi (Service B) — stop `telemetry-parser` ECS task  
**Recovery:** Yordanos — `force-new-deployment` on `telemetry-parser`  
**Evidence:** [`alerts/incident-drill-b-down-2026-08-28.txt`](alerts/incident-drill-b-down-2026-08-28.txt)

---

## Summary

Controlled production-readiness drill: stop Service B (`telemetry-parser`) to simulate **ServiceDown** on the parse hop. Ingest failed with **HTTP 502** while B was down. Recovery via ECS redeploy restored **A=2/2, B=1/1, C=1/1** and `POST /telemetry` returned **202 accepted**.

| Metric | Value |
|--------|-------|
| **TTD (operator / ECS)** | **21 s** — B `running=0` at T0+21s |
| **TTD (client / ingest)** | **~23 s** — `POST /telemetry` → **502** at T0+23s |
| **TTD (edge /health)** | **~26 s** — first `status=degraded`, `telemetry_parser=unhealthy` (after stale `reachable` on one A task) |
| **TTR (inject → healthy)** | **1 m 59 s** |
| **TTR (recovery action → healthy)** | **1 m 34 s** |

---

## Timeline (UTC)

| Time | Event | Who | Evidence |
|------|-------|-----|----------|
| **T0** `20:49:31` | **Drill announced.** Baseline: A=2/2, B=1/1, C=1/1. `/health` → `operational`, `telemetry_parser=reachable`. | Yordanos | pre-drill block in evidence file |
| `20:49:31` | Stop B task `78955cd2…` — reason: *Production readiness incident drill - ServiceDown* | Saloi (action) / Yordanos (lead) | ECS `stop-task` |
| `20:49:46` | B `running=0`, `pending=0`. ECS scheduler has not yet replaced the task. | — | ECS describe-services |
| **TTD** `20:49:52` | **Detected (operator):** B `running=0`. **Note:** `/health` on ALB still returned `operational` / `telemetry_parser=reachable` (A desired=2; healthy task served the probe). | Yordanos | detect poll 1 |
| `20:49:54` | **Detected (client):** `POST /telemetry` → **HTTP 502** — `Telemetry parser unreachable: 503 … telemetry-parser:3002/parse`. A log: `forward_to_parser` **ERROR**. | — | A CloudWatch logs |
| `20:49:56` | **Recovery started:** `aws ecs update-service … telemetry-parser --force-new-deployment` | Yordanos | recover start |
| `20:49:57`–`20:51:18` | `/health` → `degraded` / `telemetry_parser=unhealthy` on polls; B task still starting (`running=0` then `running=1` but parser not ready). | — | recover polls |
| `20:51:18` | B task `running=1`; `/health` still `unhealthy` (parser warming). | — | recover poll 8 |
| **TTR** `20:51:30` | **Recovered:** B `running=1`, `/health` → `operational`, `telemetry_parser=reachable`. | Yordanos | recover poll 9 |
| `20:51:32` | Post-recovery `POST /telemetry` → **HTTP 202 accepted**; A log `parser_response_received` success, `duration_ms: 98`. | — | post-recovery ingest |
| `20:51:33` | Final counts: A=2/2, B=1/1, C=1/1. New B task `1d673018…`. | — | final ECS table |

---

## What broke

- **Service B (`telemetry-parser`)** — task stopped; parse hop unavailable.
- **User impact:** `POST /telemetry` returned **502**; journey could not reach C or callback.
- **A remained up** behind ALB (2 tasks) but dependency check eventually showed **degraded**.

---

## Detection — what worked vs gaps

### Worked

| Signal | Result |
|--------|--------|
| ECS `runningCount` for `telemetry-parser` | **0/1 within ~21 s** — clearest operator signal |
| `POST /telemetry` | **502 within ~23 s** — clearest client signal |
| A CloudWatch logs | `forward_to_parser` **ERROR** with 503 from Service Connect |
| `/health` (eventually) | `degraded` + `telemetry_parser=unhealthy` after ~26 s |

### Gaps (see also Saloi [`callback-dns-diagnosis-2026-08-28.txt`](alerts/callback-dns-diagnosis-2026-08-28.txt) Finding 5)

| Gap | Detail |
|-----|--------|
| **No ECS Prometheus / ServiceDown page** | Compose `ServiceDown` rule does not run on the cluster; no automated page. |
| **Stale `/health` with A=2** | First probe after B stop still hit a healthy A task → `operational` / `reachable` while B was down. |
| **ALB target health ≠ journey health** | ALB marks A targets healthy; journey fails on B. |
| **Callback / silent failures** | Same class as prior callback incident — internal failures may not trip edge alerts. |

**Runbook first look:** ECS B running count → `POST /telemetry` → A logs `forward_to_parser` → `/health` JSON field `telemetry_parser` (not HTTP 200 alone).

---

## Recovery actions

1. `aws ecs update-service --cluster devops-g10-iac-cluster --service telemetry-parser --force-new-deployment`
2. Waited for B `running=1` and `/health` `telemetry_parser=reachable`
3. Verified ingest with `POST /telemetry` → 202

**Compose equivalent:** `scripts/simulate-failure.sh recover` (local only).

---

## Participants

| Name | Role | Action |
|------|------|--------|
| Yordanos Tesfay Hagos | Service A / drill lead | T0 announce, detection polls, recovery, timeline |
| Saloi | Service B | Failure inject (stop B task); B runbook context |
| Berissa | Service C | Standby; C unaffected during B-only drill |
| Arsema A. Gebremichael | Platform | ECS cluster / IAM baseline (pre-drill platform work complete) |

---

## Follow-ups (non-blocking for GO)

1. Document **A=2 sticky `/health`** as accepted lab limitation or add shared status store.
2. Add **journey-level synthetic** (POST + poll completed) — would have caught callback gap earlier.
3. Wire **ECS Container Insights or CloudWatch alarm** on `RunningTaskCount < Desired` for B.
