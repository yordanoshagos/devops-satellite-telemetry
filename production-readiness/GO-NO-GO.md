# GO / NO-GO Decision

**Date:** 2026-08-29 (final sign-off after callback proof + incident drill)  
**Account:** `240462142849` (`eu-central-1`)  
**Cluster:** `devops-g10-iac-cluster`  
**ALB:** `http://devops-g10-iac-alb-1207406256.eu-central-1.elb.amazonaws.com`  
**Drafted by:** Arsema (Platform) — final update by Yordanos (Service A)  
**Decision:** **GO**

---

## Decision summary

The rehosted ECS lab meets production-readiness criteria for the mentorship challenge:

- Services A/B/C at desired running counts **2 / 1 / 1** (verified 2026-08-29)
- ALB `/health` → **`operational`**, **`telemetry_parser=reachable`**
- Forward path **A → B → C** proven; callback **C → A** proven (`alerts/callback-completed-proof.txt`)
- **IAM roles recreated** and all services rolled (`fix/arsema-tfvars-ecr-image-shas`, platform apply 2026-08-28)
- **Incident drill** completed with TTD/TTR recorded (`incident-timeline.md`)
- **Failure-map**, **B/C alert packs**, **runbook**, and **reliability target** on `develop`

**Accepted lab limitations (not blockers):**

- **A sticky in-memory status** when `desired=2` — alternate `/status` polls may return `Request ID not found`; proof used A=1; documented in callback proof + incident timeline
- **No Prometheus/ServiceDown on ECS** — compose alerts only; ECS detection via ECS counts + `/health` JSON + ingest 502
- **Jaeger/OTLP unavailable on ECS** — compose tracing for demos

---

## Three strongest evidence items

1. **Callback journey complete** — `POST /telemetry` → **`status=completed`** in 15/15 polls with A=1 (`alerts/callback-completed-proof.txt`, mission `MISSION-COMPLETED-PROOF`).  
2. **Incident response proven** — B-down drill: TTD **21–23 s**, TTR **~2 min**, ingest restored to HTTP 202 (`incident-timeline.md`, `alerts/incident-drill-b-down-2026-08-28.txt`).  
3. **ECS baseline stable** — A=2/2, B=1/1, C=1/1; edge `/health` operational; forward path + platform IAM/SC/SG verified.

---

## Conditions (final)

| # | Condition | Status | Owner |
|---|-----------|--------|-------|
| 1 | **Status sticky / multi-task in-memory** (A desired=2) | **Accepted** — workaround: scale A→1 for status proof; document in runbook | Yordanos + Arsema |
| 2 | **Callback → completed** proof | **Closed** — `alerts/callback-completed-proof.txt` merged (#93) | Saloi + Berissa |
| 3 | **failure-map.md** (≥5 break points) | **Closed** — merged (#91 updates Break 5/7) | Saloi + Berissa |
| 4 | **B/C alerts + incident timeline** | **Closed** — drill + `incident-timeline.md` + evidence file | Yordanos + Saloi + Berissa |
| 5 | Jaeger/OTLP unavailable on ECS | **Accepted** — compose tracing for demos | Platform |
| 6 | **Recreate IAM roles + roll A/B/C** | **Closed** — terraform apply + force-new-deployment 2026-08-28; tfvars fix #92 | Yordanos / Arsema |

---

## Sign-off

| Name | Role | Vote | Notes |
|------|------|------|-------|
| Arsema A. Gebremichael | Platform | **GO** | IAM recreated; SC sidecar + callback SG verified; C on new task post-roll |
| Yordanos Tesfay Hagos | Service A | **GO** | Led incident drill; sticky `/health` + status documented as accepted limitation |
| Saloi | Service B | **GO** | B evidence + DNS diagnosis + callback completed proof merged |
| Berissa | Service C | **GO** | C alerts merged; callback completed verified on task `239246da…` |

---

## Revisit rule

**NO-GO** if baseline `/health` or running counts regress and stay broken for >15 minutes without recovery plan.

**Post-GO follow-ups (backlog, not blockers):**

1. Shared status store or sticky sessions for A when `desired>1`
2. ECS CloudWatch alarm on `RunningTaskCount < Desired` per service
3. Journey synthetic monitor (POST + poll `completed`)
