# 4. Route tables and egress

## Choices (from kickoff)

- VPC `10.10.0.0/16`
- 2 public + 2 private subnets (`eu-central-1a` / `eu-central-1b`)
- Fargate in **private** subnets only; `assign_public_ip = false`
- Egress: **NAT Gateway** (one NAT in a public subnet)

## Public route table

| Destination | Target |
|---|---|
| `10.10.0.0/16` | local |
| `0.0.0.0/0` | Internet Gateway |

## Private app route table

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
| Upside | Simpler first apply; private tasks | Lower idle cost |
| Downside | NAT hourly + data cost | More resources to wire |

Destroy NAT + ALB with workload each cycle; keep bootstrap state bucket.
