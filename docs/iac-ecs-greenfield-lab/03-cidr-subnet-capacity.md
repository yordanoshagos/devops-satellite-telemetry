# CIDR and subnet capacity



| Subnet | CIDR | AZ | Purpose |
|---|---|---|---|
| VPC | `10.10.0.0/16` | — | Custom VPC |
| Public AZ-1 | `10.10.0.0/24` | eu-central-1a | ALB + NAT |
| Public AZ-2 | `10.10.1.0/24` | eu-central-1b | ALB |
| Private app AZ-1 | `10.10.10.0/24` | eu-central-1a | Fargate tasks |
| Private app AZ-2 | `10.10.11.0/24` | eu-central-1b | Fargate tasks |

Each `/24` ≈ 251 usable IPs (enough for this lab).

## Steady-state task ENIs (approx)

| Service | Desired | Notes |
|---|---|---|
| A ground-station-api | 2 | Spread across 2 AZs |
| B telemetry-parser | 1 | |
| C anomaly-detector | 1 | |
| Service Connect proxies | ~1 per task | Extra ENI/attachment overhead |

Steady-state order of magnitude: ~4 app tasks + proxies ≪ 251 IPs per subnet.

## Rolling-deployment headroom

During an ECS rolling deploy of Service A (desired 2), AWS may temporarily run extra tasks (old + new).  
Worst-case lab planning assumption: ~**2× A** briefly (≈4 A tasks) + B + C + proxies still fits easily in two `/24` private subnets.

**Conclusion:** `10.10.10.0/24` and `10.10.11.0/24` have sufficient headroom for desired counts and rolling deploys.