# 6. Expected names and tags

## Tags (every resource)

| Key | Value |
|---|---|
| Project | `devops-mentorship` |
| Group | `group-10` |
| Owner | `service-a-owner` / `service-b-owner` / `service-c-owner` / `platform-owner` |
| Environment | `lab` |

Prefix: `devops-g10-`

## Clusters

| | Name |
|---|---|
| Console (keep) | `devops-g10-cluster` |
| IaC (new) | `devops-g10-iac-cluster` |

## Platform (IaC)

| Resource | Name |
|---|---|
| VPC | `devops-g10-iac-vpc` |
| Service Connect namespace | `group10.internal` |
| ALB | `devops-g10-iac-alb` |
| ALB SG | `devops-g10-iac-alb-sg` |
| Target group (A only) | `devops-g10-iac-tg` |
| TF state bucket | `devops-g10-tfstate-<account-id>` |

## Services

| | A | B | C |
|---|---|---|---|
| App | ground-station-api | telemetry-parser | anomaly-detector |
| ECR / task family | `devops-g10-ground-station-api` | `devops-g10-telemetry-parser` | `devops-g10-anomaly-detector` |
| ECS service | `ground-station-api` | `telemetry-parser` | `anomaly-detector` |
| SG | `devops-g10-ground-station-api-sg` | `devops-g10-telemetry-parser-sg` | `devops-g10-anomaly-detector-sg` |
| Port mapping name | `service-a` | `service-b` | `service-c` |
| Log group | `/ecs/devops-g10-ground-station-api` | `/ecs/devops-g10-telemetry-parser` | `/ecs/devops-g10-anomaly-detector` |
| Port | 3001 | 3002 | 3003 |
| Desired | 2 | 1 | 1 |

## Images

- Allowed: `sha-<git-short-sha>`
- Forbidden: `latest`
