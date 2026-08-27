# Service C alert notes — Berissa

**Service:** `anomaly-detector` (Service C)  
**Cluster:** `devops-g10-iac-cluster`  
**Log group:** `/ecs/devops-g10-iac-anomaly-detector`  
**ECR:** `240462142849.dkr.ecr.eu-central-1.amazonaws.com/devops-g10-iac-anomaly-detector`

Related compose alerts in `alert-rules.yml`: `ServiceDown`, `HighErrorRate`, `HighLatencyP95` (Prometheus → Grafana). On ECS we also use **CloudWatch Logs + ECS/CloudWatch metrics** as the availability/error signal until Prometheus scrapes the Fargate tasks.

See also: `alerts/c-observability.md` (Prometheus/Grafana vs ECS tooling map + screenshot index).

---

## Alert / signal 1 — Callback path failure (primary for C)

### What is wrong?
C receives `/analyze`, finishes anomaly detection (`event=anomaly_detection`, outcome complete), then **fails** `POST` to A `/callback`. Observed error:

`NameResolutionError: Failed to resolve 'ground-station-api'`

Log events: `callback_initiated` → `callback_sent` with `outcome=failure`.

### Why does it matter to the journey?
The critical journey is not done at analyze. Without C→A callback, status stays **`awaiting_callback`** and never **`completed`**. Users think ingest worked; results never land.

### Where do we look first?
1. CloudWatch → `/ecs/devops-g10-iac-anomaly-detector` → filter `callback_sent` or `NameResolutionError`.
2. Confirm callback URL / Service Connect DNS for A (`ground-station-api:3001` vs stale name); force new deployment if sidecar/DNS stale.
3. Confirm SG: C SG → A SG on **3001** (see `docs/iac-ecs-greenfield-lab/05-sg-matrix-traffic.md`).
4. Cross-check A log group `/ecs/devops-g10-iac-ground-station-api` for `callback_received` (absent if C never reaches A).

### Evidence
- Text capture: `alerts/baseline-e2e.txt` (health OK, POST accepted, status not completed, C callback errors).
- Screenshots:
  - `alerts/c-callback-fail.png` — CloudWatch `callback_sent` failure / NameResolutionError
  - `alerts/c-status-stuck.png` — journey stuck without `completed`
  - `alerts/c-ecs-running.png` — ECS running counts including C
  - `alerts/c-health-operational.png` — ALB `/health` still green (shows health ≠ journey success)

---

## Alert / signal 2 — Service C down (`ServiceDown` / ECS running = 0)

### What is wrong?
`anomaly-detector` is not RUNNING (desired 1, running 0) or Prometheus `up{job=~"service-.*"} == 0` in compose.

### Why does it matter to the journey?
B cannot complete `POST /analyze`; no anomaly result and no callback. Journey stops after parse.

### Where do we look first?
1. ECS → `devops-g10-iac-cluster` → service `anomaly-detector` → Tasks / Events.
2. Stopped reason (OOM, `CannotPullContainerError`, health check fail).
3. Image URI includes intended `sha-…`; private subnet NAT/ECR path if pull fails.
4. Log group `/ecs/devops-g10-iac-anomaly-detector`.

### Evidence
- Baseline (C currently up): `alerts/c-ecs-running.png` (1/1). For a down drill, capture ECS events when running=0 as `alerts/c-service-down.png`.

---

## Alert / signal 3 — High errors / latency on C (`HighErrorRate` / `HighLatencyP95`)

### What is wrong?
C returns 5xx on `/analyze` or p95 latency rises (compose: `http_errors_total` / histogram; ECS: spike of ERROR logs or slow `analyze_complete` `duration_ms`).

### Why does it matter to the journey?
Analyze is on the critical path; errors/slowness delay or block callback and completed status.

### Where do we look first?
1. C logs for `level=ERROR` and `endpoint=/analyze`.
2. B logs for downstream timeouts to C.
3. Reproduce carefully with lab `/fail` or `/slow` **only** in non-prod compose if needed; on ECS prefer read-only log/metric evidence unless the group agrees a controlled drill.

### Evidence
- Callback ERROR burst doubles as error-path evidence: `alerts/c-callback-fail.png`.

---

## Quick commands (Service C owner)

```bash
export AWS_PROFILE=g10
export AWS_REGION=eu-central-1

aws ecs describe-services --cluster devops-g10-iac-cluster \
  --services anomaly-detector \
  --query 'services[].{desired:desiredCount,running:runningCount}' --output table

aws logs tail /ecs/devops-g10-iac-anomaly-detector --since 15m --format short | grep -E 'callback_|ERROR|analyze_'
```
