# module `network`

Custom VPC for the IaC greenfield lab.

Creates:

- One VPC (`10.10.0.0/16`)
- Two public subnets across `eu-central-1a` / `eu-central-1b`
- Two private subnets across the same two AZs
- One Internet Gateway
- One NAT Gateway (in the AZ-a public subnet) with an Elastic IP
- One public route table (`0.0.0.0/0 → IGW`) associated with both public subnets
- One private route table (`0.0.0.0/0 → NAT`) associated with both private subnets

Does not create: ALB, ECS cluster, IAM roles, ECR repositories, Service Connect namespace, or any workload SGs. Those live in `alb`, `ecs-platform`, `ecs-service`, and shared IAM.

## Single-NAT trade-off

One NAT Gateway (not one per AZ) is used to control lab cost. If AZ-a or the NAT itself fails, both private subnets lose Internet egress (ECR pulls, CloudWatch Logs, ECS APIs). Acceptable for the lab because the workload is destroyed between cycles. Not acceptable for production — use one NAT per AZ or VPC endpoints for ECR/Logs/ECS/S3 instead. See `docs/iac-ecs-greenfield-lab/04-routes-egress.md`.

## Guardrails enforced by the module

- Required tag keys (`Project`, `Group`, `Owner`, `Environment`) must be present.
- Exactly two AZs, two public CIDRs, and two private CIDRs.
- `vpc_cidr` must be a valid IPv4 CIDR.
- Public subnets set `map_public_ip_on_launch = false`; the ALB assigns its own IPs and tasks live in the private subnets.

## Example usage (indicative)

```hcl
module "network" {
  source = "../../modules/network"

  tags = {
    Project     = "devops-mentorship"
    Group       = "group-10"
    Owner       = "platform-owner"
    Environment = "lab"
  }
}
```

## Outputs

| Output               | Consumer                                      |
|----------------------|-----------------------------------------------|
| `vpc_id`             | `alb`, `ecs-service` (SG), `ecs-platform`     |
| `public_subnet_ids`  | `alb`                                         |
| `private_subnet_ids` | `ecs-service` (task placement)                |
