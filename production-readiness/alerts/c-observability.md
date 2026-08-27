# Service C observability evidence — Prometheus / Grafana / CloudWatch

## Do we need Grafana/Prometheus?

**Yes, for the challenge’s ≥3 alerts story** — those alerts live in `alert-rules.yml` and are scraped via `prometheus.yml` (compose MELT stack).

**On the IaC ECS cluster today:** Prometheus, Grafana, and Jaeger are **not** deployed. So for ECS we prove the same signals with:

| Compose alert | ECS / CloudWatch substitute (captured) |
|---|---|
| `ServiceDown` | ECS running count + `LiveTaskCount` |
| `HighErrorRate` | CloudWatch Logs `ERROR` / `callback_sent` failure |
| `HighLatencyP95` | `analyze_complete` `duration_ms` in logs + CPU/mem context |

This is an explicit **GO WITH CONDITIONS** item: compose alert definitions + ECS evidence until MELT is on Fargate.

## Screenshots (Service C)

### Prometheus / Grafana (definitions from repo)
- `c-prometheus-scrape.png` — `prometheus.yml` job `service-c` → `anomaly-detector:3003/metrics`
- `c-prometheus-alerts.png` — `ServiceDown` / `HighErrorRate` / `HighLatencyP95` mapped to C
- `c-alert-tooling-map.png` — Compose ↔ ECS tooling map

### CloudWatch / ECS (live account 240462142849)
- `c-cloudwatch-cpu.png` — `AWS/ECS` CPUUtilization for `anomaly-detector`
- `c-cloudwatch-memory.png` — MemoryUtilization
- `c-cloudwatch-livetasks.png` — LiveTaskCount (ServiceDown analogue)
- `c-callback-fail.png` — HighErrorRate / journey-failure analogue
- `c-ecs-running.png` — desired/running table

## Why Grafana UI screenshots were missing earlier

The Docker **daemon was already running** on this laptop. Earlier agent checks failed because the tool sandbox blocked `/var/run/docker.sock` (looked like “Docker not working”). From a normal terminal, `docker` / `docker-compose` work.

Also: leftover stopped containers named `prometheus` / `grafana` blocked `docker-compose up` until removed with `docker rm -f prometheus grafana`.

## Live compose evidence (captured after fixing)

Stack is up via `docker-compose up -d`. ServiceDown was reproduced:

```bash
docker stop anomaly-detector   # wait ~30s for alert for: 30s
# Prometheus Alerts shows ServiceDown service-c firing
docker-compose start anomaly-detector
```

Screenshots:
- `c-grafana-servicedown-prom-alerts.png` — Prometheus Alerts UI, **ServiceDown / service-c firing**
- `c-prom-up-servicec-zero.png` — `up{job="service-c"} == 0`
- `c-grafana-home.png` / `c-grafana-explore-up.png` — Grafana reachable (`admin`/`admin`)
