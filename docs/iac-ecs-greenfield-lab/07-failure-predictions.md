# 7. Three predicted broken dependency edges


| # | Broken edge | User symptom | AWS evidence |
|---|---|---|---|
| 1 | Private tasks have no egress (NAT/route missing) or exec role cannot pull ECR | Site down; no healthy targets | Tasks stop/fail with `CannotPullContainerError`; private route table missing `0.0.0.0/0 → nat-…` |
| 2 | Missing `ALB SG → A SG` on port 3001 | 502/503 from ALB | Target group unhealthy; health check timeouts |
| 3 | IaC image tag set to `latest` or wrong SHA | Wrong/old version, or apply/tests reject | Validation/test failure; or runtime SHA ≠ expected Git SHA |

**Backup edge:** missing `C SG → A SG` (callback) → telemetry accepted but status never `completed`; errors in anomaly-detector logs to `service-a:3001`.