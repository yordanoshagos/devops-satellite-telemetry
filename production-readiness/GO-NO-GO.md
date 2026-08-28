# GO / NO-GO Decision

**Date:** 2026-08-28 (updated after platform callback verification)  
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
- Forward path **A → B → C** proven in prior logs (`Detector responded: nominal`)
- CI buildspecs retargeted to this account (merged to `develop`)
- **Failure-map**, **B/C alert notes + screenshots**, and **runbook** are on `develop`

We are **not** an unconditional GO yet:

- **`POST /telemetry` → `status=completed`** not proven (still `awaiting_callback`; see `alerts/callback-dns-diagnosis-2026-08-28.txt`)
- **`incident-timeline.md`** not merged (Yordanos drill pending)
- **P0 IAM:** roles `devops-g10-iac-cluster-task` and `devops-g10-iac-cluster-execution` **do not exist** in account `240462142849` — blocks all ECS rollouts and stopped CloudWatch log shipping ~12h ago (Saloi diagnosis 2026-08-28)

---

## Three strongest evidence items

1. **ECS running baseline** — `ground-station-api=2`, `telemetry-parser=1`, `anomaly-detector=1` (`alerts/baseline-e2e.txt`, `slo-baseline-ecs.png`).  
2. **Edge health** — ALB `/health` → `status=operational`, `telemetry_parser=reachable` (`slo-baseline-health.png`).  
3. **Forward-path proof** — B parse + detector nominal on sample ids (`baseline-e2e.txt`, B/C alert packs).

---

## Conditions (must track)

| # | Condition | Status | Owner |
|---|-----------|--------|-------|
| 1 | **Status sticky / multi-task in-memory** (A desired=2) | Open — A currently **2 desired / 1 running** (cannot place 2nd task) | Yordanos + Arsema |
| 2 | **Callback → completed** proof | Open — SC names + sidecar OK; C→A still NameResolutionError; roll blocked by missing IAM roles | Berissa + Arsema + Saloi evidence |
| 3 | **failure-map.md** (≥5 break points) | **Closed** — merged | Saloi + Berissa |
| 4 | **B/C alerts + incident timeline** | Partial — B/C notes + PNGs merged; drill + `incident-timeline.md` still open | All |
| 5 | Jaeger/OTLP unavailable on ECS | **Accepted** — compose tracing for demos | Platform |
| 6 | **Recreate g10 IAM task + execution roles** (`terraform apply`) then force-new-deployment A/B/C | **Open P0** — roles missing; see `alerts/callback-dns-diagnosis-2026-08-28.txt` Finding 4 | Yordanos / Arsema (platform) |

---

## Sign-off

| Name | Role | Vote | Notes |
|------|------|------|-------|
| Arsema A. Gebremichael | Platform | **GO WITH CONDITIONS** | Verified SC sidecar + callback SG; C roll IAM error documented |
| Yordanos Tesfay Hagos | Service A | _pending_ | Incident timeline + sticky mitigation |
| Saloi | Service B | **GO WITH CONDITIONS** | B evidence merged; DNS diagnosis filed; blocked on IAM recreate + completed proof |
| Berissa | Service C | _pending_ | C alerts merged; sign after drill |

---

## Revisit rule

Flip to **GO** only when:

1. A sample `POST /telemetry` reaches **`completed`** (or sticky-store fix shipped **and** documented), and  
2. **`incident-timeline.md`** merged with TTD/TTR, and  
3. All four sign without open SEV blockers.

Flip to **NO-GO** if baseline `/health` or running counts regress and stay broken.
