# 4. Route tables and egress

## Choices (from kickoff)

- VPC `10.10.0.0/16`
- 2 public + 2 private subnets (`eu-central-1a` / `eu-central-1b`)
- Fargate in **private** subnets only; `assign_public_ip = false`
- Egress: **one NAT Gateway** in a single public subnet (cost-controlled)

## Public route table

| Destination | Target |
|---|---|
| `10.10.0.0/16` | local |
| `0.0.0.0/0` | Internet Gateway |

## Private app route table (both private subnets share it)

| Destination | Target |
|---|---|
| `10.10.0.0/16` | local |
| `0.0.0.0/0` | NAT Gateway |

## Placement

| Component | Subnet | Public IP |
|---|---|---|
| ALB | Public ×2 AZs | ALB managed |
| NAT Gateway | Public (one AZ) | Elastic IP |
| Fargate tasks A/B/C | Private ×2 AZs | **None** |

## NAT vs endpoints

| | NAT (chosen) | VPC endpoints (not v1) |
|---|---|---|
| Upside | Simpler first apply; single egress path for tasks | Lower idle cost; no NAT single point of failure |
| Downside | NAT hourly + data cost; single-AZ NAT is a shared egress failure point | More resources to wire and test |

## Single-NAT trade-off (documented)

We deliberately run **one** NAT Gateway (not one per AZ) to control lab cost. Accepted trade-offs:

- If that AZ or the NAT itself fails, **both** private subnets lose Internet egress (ECR pulls, CloudWatch Logs, ECS APIs) even though tasks in the other AZ are otherwise healthy.
- Task-to-task traffic inside the VPC still works — the failure only affects Internet-bound egress.
- Acceptable for this lab because we destroy the workload between cycles; not acceptable for production.
- Mitigation for production: one NAT per AZ, or replace NAT with VPC interface/gateway endpoints for ECR, Logs, ECS and S3.

Destroy NAT + ALB with the workload each cycle; keep the bootstrap state bucket.
