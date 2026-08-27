# Failure map — critical journey break points

Critical journey: `POST /telemetry` → ALB → ground-station-api (A) → telemetry-parser (B) → anomaly-detector (C) → A `/callback` → status `completed`.

Owners: **Saloi** (Breaks 1–3) + **Berissa** (Breaks 4–6). Reviewers: Yordanos (A/ALB), Arsema (SG / Service Connect vs `docs/iac-ecs-greenfield-lab/05-sg-matrix-traffic.md`).

---

### Break 1 — ALB / Service A unhealthy

- **Failure:** Service A targets fail ALB health checks (bad image, crash, missing ALB→A SG on 3001, wrong health path).
- **Detect:** Target group unhealthy; ALB 5xx/timeouts; `GET /health` fails or hangs; ECS service events.
- **Absorb:** No public entry. B and C may still be RUNNING but are unreachable from clients.
- **User impact:** Client cannot ingest telemetry; curls to ALB time out or return 502/503.

### Break 2 — Service B down / wrong image

- **Failure:** `telemetry-parser` desired/running = 0, or task runs wrong app (e.g. image/context mix-up so port/behavior is not B).
- **Detect:** `/health` shows `telemetry_parser: unreachable`; A logs connection errors to B; ECS running count; CloudWatch `/ecs/devops-g10-iac-telemetry-parser`.
- **Absorb:** ALB → A may still return 200 with `status: degraded`. C idle.
- **User impact:** `POST /telemetry` may accept then fail downstream; journey never reaches analyze/callback.

### Break 3 — A→B Service Connect / security group

- **Failure:** A cannot resolve or reach B (wrong DNS name, missing A→B SG on 3002, Envoy/Service Connect misconfig).
- **Detect:** Name resolution / connection errors in A logs; `/health` dependency `unreachable`; Envoy 503s if applicable.
- **Absorb:** A stays up for ALB health; parse path broken.
- **User impact:** Ingest appears up briefly then processing fails; no completed status.

---

### Break 4 — Service C down *(Berissa)*

- **Failure:** `anomaly-detector` task stopped, crash-loop, or cannot pull image (NAT/ECR/exec role). Desired/running ≠ 1/1.
- **Detect:**
  - ECS: `anomaly-detector` running count 0 / stopped reason (`CannotPullContainerError`, etc.).
  - B logs: failures calling `anomaly-detector:3003/analyze`.
  - CloudWatch log group `/ecs/devops-g10-iac-anomaly-detector` goes quiet or shows crash loops.
  - Compose/Prometheus: `ServiceDown` on service-c if scraping compose stack.
- **Absorb:** ALB → A → B may still work through parse; analyze never runs; no callback.
- **User impact:** Telemetry may be `accepted` then stuck; status never reaches `completed` with anomaly results.

### Break 5 — C→A callback edge broken *(Berissa)*

- **Failure:** C cannot call A `/callback` — missing C→A SG on 3001, **or** Service Connect DNS for A wrong/stale (e.g. cannot resolve `ground-station-api`), or wrong `GROUND_STATION_CALLBACK_URL`.
- **Detect:**
  - C logs: `event=callback_sent` with `outcome=failure` (connection / `NameResolutionError`).
  - A `/status/<id>` stuck at `awaiting_callback` (or intermittent “not found” across A’s 2 tasks).
  - `/health` can still show `operational` + `telemetry_parser: reachable` — **do not trust health alone**.
- **Absorb:** A→B→C forward path can succeed (`/analyze` 200, anomaly detection complete); only the return path breaks.
- **User impact:** Client sees accepted/queued work that never finishes; no reliable `completed` status.
- **Evidence (2026-08-28):** `alerts/baseline-e2e.txt`, `alerts/c-callback-fail.png`, `alerts/c-status-stuck.png` — C analyzes successfully then fails callback: `Failed to resolve 'ground-station-api'`.

### Break 6 — Bad deploy / wrong immutable tag or no ECR egress *(Berissa, optional shared)*

- **Failure:** tfvars SHA points at missing/wrong image; or private tasks lose NAT/ECR egress so new tasks never start.
- **Detect:** ECS events `CannotPullContainerError`; circuit breaker rollback; running count drops; image URI in task def ≠ intended `sha-<gitsha>`.
- **Absorb:** Old tasks may keep serving until drained; rolling deploy then degrades the hop that got the bad image (for C: analyze/callback).
- **User impact:** Partial or total journey failure depending which service got the bad revision; often flaky during rollout.

---

## Mapping to traffic contract

| Edge | Port | If broken → see |
|---|---|---|
| Internet → ALB | 80 | Break 1 |
| ALB → A | 3001 | Break 1 |
| A → B | 3002 | Breaks 2–3 |
| B → C | 3003 | Break 4 |
| C → A `/callback` | 3001 | Break 5 |
| A → C (forward) | 3003 | **Denied by design** (not a break) |
