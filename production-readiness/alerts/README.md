# Alerts evidence index (platform)

**Owner:** Arsema (Platform)  
**Purpose:** Point to the ≥3 actionable alerts the group uses for the Production Readiness Challenge.

---

## Alert catalog

| Alert | Signal | Primary owner | Definition / reproduce |
|-------|--------|---------------|-------------------------|
| **ServiceDown** | Metrics (`up==0`) | Platform + service owner of the down job | `alert-rules.yml` group `service-availability` |
| **HighErrorRate** | Metrics (`http_errors_total`) | Service owner of the noisy service | `alert-rules.yml` group `service-errors` |
| **HighLatencyP95** | Metrics (histogram p95 > 0.5s) | Service owner | `alert-rules.yml` group `service-latency` |

Compose stack wires Prometheus → Alertmanager (`prometheus.yml`, `alertmanager/alertmanager.yml`).

### ECS lab signals (this account)

Until Prometheus scrapes ECS tasks directly, treat these as first-class availability signals:

1. ECS `desiredCount` vs `runningCount` for A/B/C  
2. ALB `GET /health` JSON (`operational` + B reachable)  
3. CloudWatch log groups:
   - `/ecs/devops-g10-iac-ground-station-api`
   - `/ecs/devops-g10-iac-telemetry-parser`
   - `/ecs/devops-g10-iac-anomaly-detector`

Each alert/signal must still answer: **what’s wrong**, **why it matters**, **where to look first**.

---

## Per-service note files

| File | Owner | Status |
|------|-------|--------|
| `a-notes.md` | Yordanos | On `docs/yordanos-reliability-target` |
| `b-notes.md` | Saloi | Pending (Service B owner) |
| `c-notes.md` | Berissa | Pending (Service C owner) |
| `baseline-e2e.txt` | Yordanos | Captured 2026-08-28 |

---

## Screenshot checklist (drop PNGs here)

- [ ] Prometheus `/alerts` or Grafana alert state (compose) — ServiceDown  
- [ ] HighErrorRate firing + cleared  
- [ ] HighLatencyP95 firing + cleared  
- [ ] ECS services table 2/1/1  
- [ ] ALB `/health` operational  

Name files: `alert-service-down.png`, `alert-error-rate.png`, `alert-latency.png`, `ecs-running.png`, `alb-health.png`.
