# 6. Expected names and tags

> **Correction (first real apply):** the console-based `ecs-fargate-lab` already owns
> `group10.internal`, `devops-g10-<app>` ECR repos (real pushed images), and their log
> groups. This doc originally reused those names for the IaC platform; that collides
> on create, and importing the console lab's resources into this workload's state
> would put them in this stack's `terraform destroy` path. Fixed below by extending
> the same `-iac-` disambiguator already used for the cluster/VPC/ALB to these too.

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
| Service Connect namespace | `group10-iac.internal` |
| ALB | `devops-g10-iac-alb` |
| ALB SG | `devops-g10-iac-alb-sg` |
| Target group (A only) | `devops-g10-iac-tg` |
| TF state bucket | `devops-g10-tfstate-<account-id>` |

## Services

| | A | B | C |
|---|---|---|---|
| App | ground-station-api | telemetry-parser | anomaly-detector |
| ECR / task family | `devops-g10-iac-ground-station-api` | `devops-g10-iac-telemetry-parser` | `devops-g10-iac-anomaly-detector` |
| ECS service | `ground-station-api` | `telemetry-parser` | `anomaly-detector` |
| SG | `devops-g10-iac-ground-station-api-sg` | `devops-g10-iac-telemetry-parser-sg` | `devops-g10-iac-anomaly-detector-sg` |
| Port mapping name | `service-a` | `service-b` | `service-c` |
| Log group | `/ecs/devops-g10-iac-ground-station-api` | `/ecs/devops-g10-iac-telemetry-parser` | `/ecs/devops-g10-iac-anomaly-detector` |
| Port | 3001 | 3002 | 3003 |
| Desired | 2 | 1 | 1 |

## Images

- Allowed: `sha-<git-short-sha>`
- Forbidden: `latest`
