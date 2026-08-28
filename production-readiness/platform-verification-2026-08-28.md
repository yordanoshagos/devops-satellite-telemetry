# Platform verification — callback rollout (2026-08-28)

**Operator:** Arsema (platform) — run by Yordanos on `g10-arsema`  
**Account:** `240462142849` · **Region:** `eu-central-1`  
**Cluster:** `devops-g10-iac-cluster`

---

## Step 1 — Force-new-deployment on `anomaly-detector`

```bash
aws ecs update-service --cluster devops-g10-iac-cluster \
  --service anomaly-detector --force-new-deployment
```

**Result:** New deployment **did not replace** the running task. ECS event:

> `(service anomaly-detector) failed to launch a task with (error ECS was unable to assume the role 'arn:aws:iam::240462142849:role/devops-g10-iac-cluster-task' ...)`

PRIMARY deployment stayed `IN_PROGRESS` with `running=0`; previous ACTIVE deployment remained `COMPLETED` with `running=1`. **Service stayed up** on the old task.

**Action for platform:** Investigate IAM task role trust / PassRole on next apply window (not blocking health, but blocks clean rollouts).

---

## Step 2 — Service Connect sidecar on running C task

Running task: `b53f40fd75ed4576aeefe694288d6712`  
Task definition: `devops-g10-iac-anomaly-detector:1`

Container names:

```json
["ecs-service-connect-4YW5j", "anomaly-detector"]
```

**Pass** — Service Connect sidecar is present on the live task.

---

## Step 3 — Security group C → A (callback on 3001)

On `devops-g10-iac-ground-station-api-sg`, TCP 3001 includes:

| Source SG | Description |
|-----------|-------------|
| `sg-003b447262a09184c` | Callback from C to A on 3001 |
| `sg-08358de15cebe4ce8` | ALB → A |

**Pass** — Terraform `callback_c_to_a` rule is applied in AWS.

---

## Step 4 — Callback / completion proof (post-roll attempt)

Sample `POST /telemetry` → `processing_request_id=e18154fb-caec-4434-a0af-01a97593a499`

Poll results (10 × `/status/<id>`):

- Alternating **`awaiting_callback`** and **`Request ID not found`**
- **No** `"status":"completed"` observed

**Interpretation:**

1. **A desired=2 + in-memory status** — ALB spreads `/telemetry`, `/status`, and `/callback` across tasks (sticky issue; condition #1 in GO-NO-GO).
2. Roll did not refresh C (IAM error); existing C task already had Service Connect — callback completion is not fixed by roll alone.

**Handoff:** Saloi can still capture B parse logs for the id; Yordanos should run incident drill only after team agrees on sticky mitigation (scale A to 1 for proof, or accept conditional GO).

---

## ECS counts at verification time

| Service | Desired | Running |
|---------|---------|---------|
| ground-station-api | 2 | 2 |
| telemetry-parser | 1 | 1 |
| anomaly-detector | 1 | 1 |

ALB `/health`: `operational`, `telemetry_parser=reachable`.
