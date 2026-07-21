# 4. Ownership Map and Expected Resource Names

> Part of Gate 1 submission — see [README.md](./README.md) for the full folder index.

---

## 5. Ownership map and expected resource names

### 5a. Ownership

| Team member | Role | Owns |
|---|---|---|
| Yordanos | Service A owner | ground-station-api image, ECR, task def, SG, ECS service, pipeline |
| Saloi | Service B owner | telemetry-parser image, ECR, task def, SG, ECS service, pipeline |
| Berissa | Service C owner | anomaly-detector image, ECR, task def, SG, ECS service, pipeline |
| Arsema | Platform owner | Cluster, Service Connect namespace, ALB, target group, CodeConnections |

**Working rules:** each owner operates their own console. Team observes and
diagnoses aloud; evidence decides. Owners may advise but must not operate another
owner's resources.

### 5b. Expected resource names

All names begin with `devops-g10-`. Every resource carries the four tags:
`Project=devops-mentorship`, `Group=group-10`, `Owner=<role>-owner`,
`Environment=lab`.

**Platform-owned (Arsema)**

| Resource | Name |
|---|---|
| ECS cluster | `devops-g10-cluster` |
| Service Connect namespace | `group10.internal` |
| ALB | `devops-g10-alb` |
| ALB security group | `devops-g10-alb-sg` |
| Target group (ground-station-api) | `devops-g10-tg` |
| CodeConnections connection | `devops-g10-github` |

**Service A owner (Yordanos)**

| Resource | Name |
|---|---|
| ECR repository | `devops-g10-ground-station-api` |
| Task definition family | `devops-g10-ground-station-api` |
| ECS service | `ground-station-api` |
| Container name | `ground-station-api` |
| Security group | `devops-g10-ground-station-api-sg` |
| Port mapping name | `service-a` |
| CloudWatch log group | `/ecs/devops-g10-ground-station-api` |
| CodeBuild project | `devops-g10-ground-station-api-build` |
| Pipeline | `devops-g10-ground-station-api-pipeline` |
| Buildspec (repo) | `buildspecs/service-a.yml` |
| Desired count | 2 |

**Service B owner (Saloi)**

| Resource | Name |
|---|---|
| ECR repository | `devops-g10-telemetry-parser` |
| Task definition family | `devops-g10-telemetry-parser` |
| ECS service | `telemetry-parser` |
| Container name | `telemetry-parser` |
| Security group | `devops-g10-telemetry-parser-sg` |
| Port mapping name | `service-b` |
| CloudWatch log group | `/ecs/devops-g10-telemetry-parser` |
| CodeBuild project | `devops-g10-telemetry-parser-build` |
| Pipeline | `devops-g10-telemetry-parser-pipeline` |
| Buildspec (repo) | `buildspecs/service-b.yml` |
| Desired count | 1 |

**Service C owner (Berissa)**

| Resource | Name |
|---|---|
| ECR repository | `devops-g10-anomaly-detector` |
| Task definition family | `devops-g10-anomaly-detector` |
| ECS service | `anomaly-detector` |
| Container name | `anomaly-detector` |
| Security group | `devops-g10-anomaly-detector-sg` |
| Port mapping name | `service-c` |
| CloudWatch log group | `/ecs/devops-g10-anomaly-detector` |
| CodeBuild project | `devops-g10-anomaly-detector-build` |
| Pipeline | `devops-g10-anomaly-detector-pipeline` |
| Buildspec (repo) | `buildspecs/service-c.yml` |
| Desired count | 1 |

**Image tagging:** `sha-<git-short-sha>` only (e.g. `sha-b97b3d0`); never `latest`.  
**Example URI:** `827478161993.dkr.ecr.eu-central-1.amazonaws.com/devops-g10-telemetry-parser:sha-b97b3d0`
