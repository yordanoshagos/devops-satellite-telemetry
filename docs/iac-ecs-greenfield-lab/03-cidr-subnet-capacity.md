# 3. CIDR and subnet capacity

## Subnets

| Subnet | CIDR | AZ | Purpose |
|---|---|---|---|
| VPC | `10.10.0.0/16` | — | Custom VPC |
| Public AZ-1 | `10.10.0.0/24` | eu-central-1a | ALB + NAT |
| Public AZ-2 | `10.10.1.0/24` | eu-central-1b | ALB |
| Private app AZ-1 | `10.10.10.0/24` | eu-central-1a | Fargate tasks |
| Private app AZ-2 | `10.10.11.0/24` | eu-central-1b | Fargate tasks |

Each `/24` = 256 addresses. AWS reserves 5 per subnet (network, VPC router, DNS, future, broadcast) → **~251 usable**.

## What consumes IPs (basis for estimates)

We size subnets based on the following per-AZ consumers, **not** a separate ENI per Service Connect proxy (the proxy runs alongside the task and does not add its own subnet ENI):

- Fargate task ENIs (one ENI per running task on `awsvpc`).
- ECS rolling-deployment replacements (extra tasks briefly during a deploy).
- ALB networking ENIs in each public subnet.
- AWS-reserved addresses (5 per subnet).

## Steady state per AZ

| Consumer | ENIs per AZ (steady state) |
|---|---|
| Service A tasks (desired 2, spread across 2 AZs) | ~1 |
| Service B tasks (desired 1) | 0–1 |
| Service C tasks (desired 1) | 0–1 |
| ALB ENIs (in public subnet only) | 1–2 |
| AWS-reserved (private subnet) | 5 |

Well under 251 addresses per `/24`.

## Rolling-deployment headroom

During a rolling deploy of Service A (desired 2), ECS may temporarily run additional replacement tasks alongside the old ones. Worst case in this lab is approximately double the desired count for a short period, plus B and C unchanged.

Even doubling A across the two private subnets (≈4 A ENIs + B + C + reserved) uses far fewer than 251 addresses per `/24`.

**Conclusion:** `10.10.10.0/24` and `10.10.11.0/24` have ample headroom for desired counts, rolling deploys, and AWS-reserved addresses. Public `/24`s comfortably fit ALB and NAT ENIs.
