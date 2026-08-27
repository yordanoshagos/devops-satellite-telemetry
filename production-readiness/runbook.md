# Runbook — ALB / telemetry journey degraded

**Owner:** Arsema (Platform), covering while primary platform owner is away  
**Supports:** Yordanos (A), Saloi (B), Berissa (C)  
**Environment:** account `240462142849`, `eu-central-1`, cluster `devops-g10-iac-cluster`  
**ALB:** `http://devops-g10-iac-alb-1207406256.eu-central-1.elb.amazonaws.com`

---

## 1. Trigger

Use this runbook when any of the following appear:

- `GET $ALB/health` is not `operational` / `telemetry_parser` not `reachable`
- `POST $ALB/telemetry` fails (5xx/timeout) or never accepts
- `GET $ALB/status/<id>` stuck on `awaiting_callback` or returns `Request ID not found`
- ECS runningCount < desired for A/B/C
- Page from on-call: “telemetry not completing”

---

## 2. Verify impact (5 minutes)

```bash
export AWS_PROFILE=g10-arsema   # or your SSO profile for 240462142849
export AWS_REGION=eu-central-1
ALB=http://devops-g10-iac-alb-1207406256.eu-central-1.elb.amazonaws.com

aws ecs describe-services \
  --cluster devops-g10-iac-cluster \
  --services ground-station-api telemetry-parser anomaly-detector \
  --query 'services[].{name:serviceName,desired:desiredCount,running:runningCount}' \
  --output table

curl -sS "$ALB/health"
```

**Impact levels**

| Observation | Impact |
|-------------|--------|
| A running < 2 or `/health` down | **High** — ingest edge broken |
| B running = 0 or unreachable from A | **High** — journey stops after accept |
| C running = 0 | **Medium/High** — analyze/callback path broken |
| `/health` operational but status stuck `awaiting_callback` | **Medium** — forward path may work; completion SLO burns |

Record clock time as **T_detect** for the incident timeline.

---

## 3. Diagnose (branch by symptom)

### 3A — `/health` degraded / B unreachable

```bash
aws logs tail /ecs/devops-g10-iac-telemetry-parser --since 30m --format short | head -40
```

Confirm startup line is **`telemetry-parser` … port 3002** (not `anomaly-detector` / 3003).  
Wrong image in B’s ECR was a real incident on this account — immutable tags cannot be overwritten; push a new `sha-<hex>` and update `service-b.auto.tfvars`.

Also check Service Connect / Envoy 503 from A:

```bash
TASK=$(aws ecs list-tasks --cluster devops-g10-iac-cluster \
  --service-name ground-station-api --desired-status RUNNING \
  --query 'taskArns[0]' --output text)
aws ecs execute-command --cluster devops-g10-iac-cluster --task "$TASK" \
  --container ground-station-api --interactive --command "/bin/sh"
# inside:
# python -c "import urllib.request; print(urllib.request.urlopen('http://telemetry-parser:3002/health', timeout=5).read())"
```

**B owner — wrong-image / SG check (Saloi):**

```bash
export AWS_PROFILE=g10 AWS_REGION=eu-central-1
CLUSTER=devops-g10-iac-cluster

TD=$(aws ecs describe-services --cluster "$CLUSTER" --services telemetry-parser \
  --query 'services[0].taskDefinition' --output text)
aws ecs describe-task-definition --task-definition "$TD" \
  --query 'taskDefinition.containerDefinitions[0].{name:name,image:image,port:portMappings}'
# Must be name=telemetry-parser, port 3002,
# image .../devops-g10-iac-telemetry-parser:sha-<gitsha>

aws logs tail /ecs/devops-g10-iac-telemetry-parser --since 15m --format short
# JSON must say "service": "telemetry-parser" and POST /parse — not ground-station-api/3001

aws ec2 describe-security-groups --group-ids sg-0140cb7d6e278027f \
  --query 'SecurityGroups[0].IpPermissions'
# Expect tcp/3002 from sg-03a16c74e29412014 (ground-station-api-sg)
```

If parse logs exist for the request id but `/status` stays `awaiting_callback`, this is **not** a B image rollback — escalate to Berissa (callback / C).

### 3B — Accept works, status stuck `awaiting_callback`

1. Confirm B received parse + `Detector responded` for the `processing_request_id`.  
2. Confirm C logs show analyze + callback attempt to `http://ground-station-api:3001/callback`.  
3. Confirm SG rule **C→A on 3001** exists (Terraform `callback_c_to_a`).  
4. Remember A **desired=2** with **in-memory** status: ALB may send `/status` or `/callback` to a different task than the accepter → `Request ID not found` or never completes.

### 3C — ECS tasks not running

```bash
aws ecs describe-services --cluster devops-g10-iac-cluster \
  --services ground-station-api telemetry-parser anomaly-detector \
  --query 'services[].events[0:5]' --output table
```

Check stopped task reasons, image pull errors, health check failures.

---

## 4. Mitigate

| Cause | Mitigation |
|-------|------------|
| Wrong B image | Build from **`service-b` only**, push new hex tag `sha-[0-9a-f]{7,40}`, update `service-b.auto.tfvars`, `terraform apply` |
| Bad deploy / stuck roll | `aws ecs update-service --cluster devops-g10-iac-cluster --service <name> --force-new-deployment` |
| Missing callback SG | Re-apply lab stack / restore `callback_c_to_a` (platform only; one apply at a time) |
| Status sticky/multi-task gap | Short-term: scale A to 1 for drill validation; long-term: shared status store (tracked in GO-NO-GO conditions) |

---

## 5. Recover

Wait for:

```bash
aws ecs describe-services --cluster devops-g10-iac-cluster \
  --services ground-station-api \
  --query 'services[0].deployments[].{status:status,rollout:rolloutState,running:runningCount}' \
  --output table
```

PRIMARY + `COMPLETED` and desired==running.

---

## 6. Validate (journey — not just “task running”)

```bash
ALB=http://devops-g10-iac-alb-1207406256.eu-central-1.elb.amazonaws.com
curl -sS "$ALB/health"
# must be operational + telemetry_parser reachable

RESP=$(curl -sS -X POST "$ALB/telemetry" -H "Content-Type: application/json" -d '{
  "satellite_id": "SAT-001",
  "mission_id": "MISSION-PR-RECOVER",
  "timestamp": "2026-08-28T00:00:00Z",
  "telemetry_frame": {
    "battery_voltage": 14.2,
    "solar_panel_temp": 45.3,
    "gyro_x": 0.01, "gyro_y": -0.02, "gyro_z": 0.0,
    "signal_strength_dbm": -85,
    "downlink_frequency": 437.5
  }
}')
echo "$RESP"
# poll status with processing_request_id until completed OR document still-awaiting_callback as open condition
```

Record **T_recover** when validation passes (or explicitly note residual gap).

---

## 7. Escalate

| If… | Escalate to |
|-----|-------------|
| A/ALB / target group | Yordanos |
| B image / parse path | Saloi |
| C analyze / callback | Berissa |
| Terraform / SG / Service Connect / account | Arsema (platform) |
| No progress > 30 minutes | Whole group + mentor; freeze deploys |

---

## Related evidence

- Reliability target: `reliability-target.md`
- Failure map: `failure-map.md`
- Alert index: `alerts/README.md` (B: `alerts/b-notes.md`)
- GO / NO-GO: `GO-NO-GO.md`
