# Failure map — critical journey

**Journey:** Client → ALB → `ground-station-api` (A) → `telemetry-parser` (B) → `anomaly-detector` (C) → callback → `/status` completed

**Shared truth**

| | |
|---|---|
| ALB | `http://devops-g10-iac-alb-1207406256.eu-central-1.elb.amazonaws.com` |
| Cluster | `devops-g10-iac-cluster` |
| Account / region | `240462142849` / `eu-central-1` |
| Namespace | `group10-iac.internal` |
| Traffic contract | [`docs/iac-ecs-greenfield-lab/05-sg-matrix-traffic.md`](../docs/iac-ecs-greenfield-lab/05-sg-matrix-traffic.md) |

**Owners:** Saloi (breaks 1–3) · Berissa (breaks 4–6)  
**Review:** Yordanos (A/ALB rows) · Arsema (SG / Service Connect wording)

**Live Day 0 (2026-08-27T23:14Z):** A→B→C data path works. C→A callback does **not**. See [`alerts/baseline-e2e.txt`](alerts/baseline-e2e.txt).

---

### Break 1 — ALB / Service A unhealthy

- **Failure:** ALB cannot reach healthy Service A targets on port 3001. Typical causes: A tasks crashed or not running; missing `devops-g10-iac-alb-sg` → `devops-g10-iac-ground-station-api-sg` TCP 3001 (same class as SCAR-003 on the old console lab); A image/task never becomes healthy.
- **Detect:**
  - `curl -sS --max-time 10 "$ALB/health"` → timeout, 5xx, or empty body
  - ECS: `ground-station-api` `runningCount` < `desiredCount` (2)
  - Target group `devops-g10-iac-tg` unhealthy / request timed out
  - Compose: `HighErrorRate` on A if A is up but returning 5xx; ALB 5xx in access logs if enabled
- **Absorb:** Nothing public works. B and C can still be running (private). No client path into the journey.
- **User impact:** Client sees connection timeout, 502, or 503. No `processing_request_id`. Telemetry ingest is down.

---

### Break 2 — Service B down / wrong image

- **Failure:** `telemetry-parser` is the parse hop. Two ways we have already lived this:
  1. **B down:** desired 0, task stopped, crash, or `CannotPullContainerError` (NAT/ECR). Desired is **1** — there is no spare task.
  2. **Wrong image:** placeholder `0000000`, arm64 image on Fargate amd64, or a non-parser image tagged into B's task def. Symptom: task running but logs are not `"service":"telemetry-parser"` on port **3002**.
- **Detect:**
  - `/health` still HTTP 200 (A always returns 200) but `"status":"degraded"` and `"telemetry_parser"` not `reachable`
  - `POST /telemetry` → HTTP 502 `Telemetry parser unreachable`
  - ECS: `telemetry-parser` running 0/1; events: stopped task / deployment failed
  - Logs: `aws logs tail /ecs/devops-g10-iac-telemetry-parser --since 10m` — silence, or wrong service name, or no `POST /parse`
  - Compose: `ServiceDown` on `job=service-b` after `docker compose stop telemetry-parser` (~30s)
- **Absorb:** ALB and A stay up. `/health` looks “fine” at the HTTP layer. C is idle. The parse path is dead.
- **User impact:** Client can still hit the ALB. Ingest returns **502**. No completed status. Critical journey fails at A→B.

**Wrong-image first check (B owner):**

```bash
export AWS_PROFILE=g10 AWS_REGION=eu-central-1
aws ecs describe-services --cluster devops-g10-iac-cluster --services telemetry-parser \
  --query 'services[0].{desired:desiredCount,running:runningCount,td:taskDefinition}'
# Expect image .../devops-g10-iac-telemetry-parser:sha-<gitsha>
# Expect portMappings.containerPort=3002 and container name telemetry-parser
aws logs tail /ecs/devops-g10-iac-telemetry-parser --since 5m --format short
# Must contain "service": "telemetry-parser" and listen/parse on 3002 — not ground-station-api/3001
```

Day 0 running image (good): `.../devops-g10-iac-telemetry-parser:sha-aeb45210` on `devops-g10-iac-telemetry-parser:3`.

---

### Break 3 — A→B Service Connect / security group

- **Failure:** A cannot open TCP 3002 to B even if both tasks are RUNNING.
  - **SG:** B inbound must be `devops-g10-iac-ground-station-api-sg` (`sg-03a16c74e29412014`) → `devops-g10-iac-telemetry-parser-sg` (`sg-0140cb7d6e278027f`) TCP **3002**. Internet must **not** reach B (no `0.0.0.0/0` on 3002). Observed Day 0: that SG reference **is** present.
  - **Service Connect:** A calls `http://telemetry-parser:3002` (`TELEMETRY_PARSER_URL` default). Client alias in namespace `group10-iac.internal` must be `telemetry-parser` port 3002. If the alias is wrong (historical `service-b` name), A gets connection errors / Envoy 503. PR `fix/service-connect-dns-app-names` aligned aliases with app hostnames.
- **Detect:**
  - `/health` → `telemetry_parser` unreachable / unhealthy while B `runningCount=1`
  - A logs `event=forward_to_parser` `outcome=failure`
  - B logs: no `parse_request` for that id (packet never arrived)
  - Compare ECS Service Connect `clientAliases.dnsName` to the URL in A logs
- **Absorb:** Public ALB→A still works. B process may be healthy. C idle. Same user-visible 502 as Break 2 — distinguish with: B running + SG/DNS vs B not running.
- **User impact:** `POST /telemetry` 502. Journey stops at A→B.

**Day 0:** A→B **works** (`telemetry_parser: reachable`, parse 200). The broken discovery we captured is the **return** hop (C→A, Break 5), not A→B.

---

### Break 4 — Service C down

- **Failure:** `anomaly-detector` desired 1; task stopped, bad image, or pull failure. B can still parse.
- **Detect:**
  - B logs: `forward_to_detector` then timeout / connection error to `http://anomaly-detector:3003/analyze`
  - ECS: `anomaly-detector` running 0/1
  - Log group `/ecs/devops-g10-iac-anomaly-detector` silent or stopped-task events
  - Compose: `ServiceDown` on `job=service-c`
- **Absorb:** `/health` can stay `operational` (A only probes B, not C — traffic contract denies A→C). `POST /telemetry` may 5xx from B if B fails the C call, or accept-then-stick if B swallows it.
- **User impact:** Ingest does not complete analysis. Status never `completed`.

*Berissa: confirm exact B status code when C is down, and add your screenshot.*

---

### Break 5 — C→A callback (SG **or** Service Connect DNS)

- **Failure:** Pipeline A→B→C runs, then C cannot `POST /callback` to A.
  - **SG (predicted):** missing `devops-g10-iac-anomaly-detector-sg` → `devops-g10-iac-ground-station-api-sg` TCP 3001. Same class as SCAR-004.
  - **DNS (observed Day 0, 2026-08-27T23:14Z):** SG path is not the current break. C logs:
    > Failed to send callback to Ground Station: … `NameResolutionError` … Failed to resolve `'ground-station-api'` (`[Errno -2] Name or service not known`)
    C uses `GROUND_STATION_CALLBACK_URL` default `http://ground-station-api:3001/callback`. Service Connect on A advertises `dnsName=ground-station-api` port 3001 in `group10-iac.internal`, and B **can** resolve `anomaly-detector`. C still cannot resolve `ground-station-api`. Every sampled request in the window failed the same way (including `pr-baseline-berissa-001`).
- **Detect:**
  - `/status/<id>` stuck at `awaiting_callback` (or 404 `Request ID not found` on the other A replica)
  - C logs `event=callback_sent` `outcome=failure`
  - A logs: no `event=callback_received` for that id
  - `/health` still `operational` — ALB→A and A→B are intact
- **Absorb:** Parse + analyze succeed (B returns 200 to A). Client gets `accepted` then a status that never completes. Easy to mistake for “green” if you only curl `/health`.
- **User impact:** Critical journey **fails**. Client cannot see `completed`.

*Berissa: own the DNS vs SG split; attach C log screenshot. Saloi captured the text in `alerts/baseline-e2e.txt`.*

---

### Break 6 — Bad deploy / immutable wrong tag / NAT–ECR pull

- **Failure:** Task definition points at a SHA that is not in ECR, wrong architecture, or private subnet has no NAT so Fargate cannot pull. Circuit breaker may roll back; or the service sits at running 0.
- **Detect:** ECS service events `CannotPullContainerError` / `deployment failed`; task stopped reason; image URI ≠ intended `sha-<gitsha>`.
- **Absorb:** Previous revision may still serve if circuit breaker rollback=true. If not, that service’s hop is down (Break 2 or 4).
- **User impact:** Depends which service’s image broke. For B: same as Break 2 (502 ingest).

*Berissa: optional; add NAT/ECR evidence if you have a scar.*

---

## Extra detection gaps (not extra break rows — they change how we page)

1. **A `/health` is always HTTP 200.** Degraded B still looks like a healthy ALB target. Do not use ALB target-health alone for the parse path — read the JSON `telemetry_parser` field and B running count.
2. **A `request_store` is in-memory and A desired=2.** `GET /status/<id>` load-balances; ~half the responses are `Request ID not found` even when the other replica has `awaiting_callback`. Success SLI “% completed” is not measurable through the ALB without sticky sessions or shared state.
3. **Prometheus `ServiceDown` is compose-only.** ECS lab signal for B is CloudWatch + ECS running count + `/health` JSON, not `up{job="service-b"}`.

---

## Sign-off

| Name | Role | Breaks | Status |
|---|---|---|---|
| Saloi | Service B | 1, 2, 3 + Day 0 evidence | Written 2026-08-28 |
| Berissa | Service C | 4, 5, 6 | Drafted from live C logs — please confirm/replace |
| Yordanos | Service A | Review 1 | |
| Arsema | Platform | Review SG / Service Connect vs `05-sg-matrix-traffic.md` | |
