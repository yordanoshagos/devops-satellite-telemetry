# 4. Route tables and egress design

**Author:** Arsema (Platform)  
**Reviewer:** Saloi  
**Group:** 10 · **Region:** `eu-central-1`

---

## Locked choices (from kickoff)

- Custom VPC `10.10.0.0/16`
- 2 public + 2 private subnets across `eu-central-1a` / `eu-central-1b`
- Fargate tasks in **private** subnets only
- `assign_public_ip = false`
- Egress: **NAT Gateway** (lab default — faster first apply than full endpoint set)

---

## Route tables

### Public route table (both public subnets)

| Destination | Target | Why |
|---|---|---|
| `10.10.0.0/16` | local | VPC traffic |
| `0.0.0.0/0` | Internet Gateway | ALB clients in; NAT can reach Internet out |

### Private app route table (both private subnets)

| Destination | Target | Why |
|---|---|---|
| `10.10.0.0/16` | local | VPC traffic (ALB→task is via TG to task ENI in VPC) |
| `0.0.0.0/0` | NAT Gateway | ECR pull, CloudWatch Logs, ECS APIs, image layers |

---

## What sits where

| Component | Subnet type | Public IP |
|---|---|---|
| Internet-facing ALB | Public ×2 AZs | ALB managed |
| NAT Gateway | Public (one AZ for lab cost control) | Elastic IP |
| Fargate tasks A/B/C | Private ×2 AZs | **None** |
| VPC endpoints | Not used in v1 (NAT chosen) | n/a |

---

## Egress decision (summary for decision card #2 companion)

| | NAT Gateway (chosen) | VPC endpoints (not chosen for v1) |
|---|---|---|
| Risk reduced | Tasks leave private; no public task IPs | No NAT hourly cost; tighter egress |
| Trade-off accepted | NAT hourly + data cost | More endpoint resources to wire and test |
| Evidence it works | Route table shows `0.0.0.0/0 → nat-…`; task pulls image; CW logs appear; `terraform state` shows NAT | Interface endpoints + pull success without NAT |

**Cost note:** Destroy workload (including NAT + ALB) after each cycle; keep only bootstrap state bucket.

---

## Evidence we will capture after apply

1. Screenshot / CLI: private route table `0.0.0.0/0` → `nat-…`
2. ECS task networking: **no** public IP on running tasks
3. Task reaches `RUNNING` (proves ECR pull via NAT)
4. CloudWatch log streams for A/B/C exist
