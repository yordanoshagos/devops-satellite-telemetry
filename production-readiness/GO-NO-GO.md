# GO / NO-GO Decision

**Date:** 2026-08-28  
**Account:** `240462142849` (`eu-central-1`)  
**Cluster:** `devops-g10-iac-cluster`  
**ALB:** `http://devops-g10-iac-alb-1207406256.eu-central-1.elb.amazonaws.com`  
**Drafted by:** Arsema (Platform) — operated by Yordanos while Arsema is away  
**Decision:** **GO WITH CONDITIONS**

---

## Decision summary

The rehosted ECS baseline is **alive and useful**:

- Services A/B/C at desired running counts **2 / 1 / 1**
- ALB `/health` returns **`operational`** with **`telemetry_parser=reachable`**
- Forward path **A → B → C** proven in logs (`Detector responded: nominal`)
- CI buildspecs retargeted to this account (merged to `develop`)

We are **not** a clean unconditional GO yet: the critical journey’s terminal step (**C → A callback / completed status**) is still unreliable in this lab (status stuck `awaiting_callback`; intermittent `Request ID not found` with A desired=2 in-memory state). Failure-map, B/C alert screenshots, and the controlled incident timeline are still owned by the wider group.

---

## Three strongest evidence items

1. **ECS running baseline** — `ground-station-api=2`, `telemetry-parser=1`, `anomaly-detector=1` (captured in Yordanos `alerts/baseline-e2e.txt`).  
2. **Edge health** — ALB `/health` → `status=operational`, `telemetry_parser=reachable`.  
3. **Forward-path proof** — same capture: `POST /telemetry` accepted; B parse + detector nominal for `processing_request_id=1578c224-3c92-4920-9c6b-80e24141e648`.

---

## Conditions (must track)

| # | Condition | Owner to close |
|---|-----------|----------------|
| 1 | Document and fix or accept **status sticky / multi-task in-memory** gap (A desired=2) | Yordanos + Arsema |
| 2 | Prove **callback completion** (status → completed) or record as known SEV in failure-map | Berissa + Arsema |
| 3 | Saloi/Berissa complete **failure-map.md** (≥5 break points) | Saloi drafted 1–6 (Berissa confirm 4–6) |
| 4 | Add **B/C alert notes + firing screenshots**; finish incident drill + `incident-timeline.md` | B notes + ServiceDown PNGs landed; C notes + drill still open |
| 5 | Jaeger/OTLP unavailable on ECS (noisy logs) — accept compose tracing for now | Platform |

---

## Sign-off

| Name | Role | Vote | Notes |
|------|------|------|-------|
| Arsema A. Gebremichael | Platform | **GO WITH CONDITIONS** | Drafted; conditions above |
| Yordanos Tesfay Hagos | Service A | _pending on PR review_ | Reliability target + A alerts landed |
| Saloi | Service B | **GO WITH CONDITIONS** | B parse proven in CloudWatch; callback DNS still fails so `/status` never `completed` |
| Berissa | Service C | _pending_ | failure-map + c-notes + callback proof |

---

## Revisit rule

Flip to **GO** only when:

1. A sample `POST /telemetry` reaches **completed** status (or sticky-store fix is shipped), and  
2. failure-map + alert screenshots + incident timeline are merged, and  
3. All four sign below without open SEV blockers.

Flip to **NO-GO** if baseline `/health` or running counts regress and stay broken.
