# 3. Failure Predictions

> Part of Gate 1 submission — see [README.md](./README.md) for the full folder index.

---

## 3. Failure predictions

Three edges we will re-test in Phase 4.

| Broken edge | Expected user symptom | Expected AWS evidence |
|---|---|---|
| Execution role missing ECR-pull permission (task → ECR) | Site down; ALB returns 503, no version served | Task never reaches RUNNING; stopped-task reason `CannotPullContainerError` in ECS service events |
| ground-station-api bound to 127.0.0.1 instead of 0.0.0.0 | Intermittent then total 502/503 from the ALB | Container RUNNING but target group shows target `unhealthy`; health-check connection refused |
| Missing `ALB SG → ground-station-api SG` rule (ALB → A) | 502/503; requests hang then fail at the ALB | Target group health `unhealthy` with health-check timeouts; no inbound flow reaching ground-station-api |

**Backup edge to watch:** missing `anomaly-detector SG → ground-station-api SG`
(callback). Symptom: telemetry accepted but processing status never updates.
Evidence: connection errors in anomaly-detector logs toward `service-a:3001`.
