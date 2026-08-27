# Service A alert notes

**Owner:** Yordanos  
**Service:** `ground-station-api`  
**Repo alerts (compose):** `alert-rules.yml` → `ServiceDown`, `HighErrorRate`, `HighLatencyP95`

---

## Alert 1 mapping — Availability / ServiceDown (A)

| Field | Content |
|-------|---------|
| What is wrong? | A is not scrapable / not serving `/health` operationally, or ALB targets unhealthy |
| Why it matters? | Clients cannot ingest telemetry; critical journey stops at the edge |
| Where to look first? | `curl $ALB/health`; ECS running count for `ground-station-api`; log group `/ecs/devops-g10-iac-ground-station-api`; ALB target group health |

**Lab reproduce (ECS):**
```bash
export AWS_PROFILE=g10-arsema AWS_REGION=eu-central-1
TASK=$(aws ecs list-tasks --cluster devops-g10-iac-cluster \
  --service-name ground-station-api --desired-status RUNNING \
  --query 'taskArns[0]' --output text)
aws ecs stop-task --cluster devops-g10-iac-cluster --task "$TASK" \
  --reason "PR challenge: A availability drill"
```
Expect: brief blip on `/health` or target count; ECS replaces the task.

**Confirm normal:** runningCount returns to 2; `/health` shows `operational` + `telemetry_parser=reachable`.

---

## Alert 2 mapping — HighErrorRate (A)

| Field | Content |
|-------|---------|
| What is wrong? | Elevated 5xx from A (or failed dependency handling on ingest) |
| Why it matters? | Accepted/ingest path fails; satellites cannot deliver frames |
| Where to look first? | A logs `level=ERROR` / `outcome=failure` on `/telemetry`; B reachability; Service Connect 503s to `telemetry-parser` |

**Compose reproduce (local MELT):** `curl` loop against `/fail` or `scripts/load-test.sh failure` (see `alert-rules.yml` annotations).

**ECS note:** Prefer CloudWatch filter on `endpoint="/telemetry"` failures if Prometheus is not scraping ECS tasks yet.

---

## Alert 3 mapping — HighLatencyP95 (A)

| Field | Content |
|-------|---------|
| What is wrong? | p95 request latency on A above 500ms (compose rule) / above SLO 2s for ingest |
| Why it matters? | Slow accept path burns latency SLO even if availability looks fine |
| Where to look first? | A log `duration_ms` on `/telemetry`; B `/health` latency; Envoy 503/timeouts |

---

## Evidence pointers

- Baseline capture: `baseline-e2e.txt`
- Reliability target / SLOs: `../reliability-target.md`
- Platform alert index: `README.md` (Arsema)
