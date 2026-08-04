# module `alb`

Internet-facing Application Load Balancer for Service A (`ground-station-api`) in the IaC greenfield lab.

Creates:

- ALB security group (`devops-g10-iac-alb-sg`) — inbound TCP 80 from `0.0.0.0/0` only
- Target group type **`ip`** (`devops-g10-iac-tg`) — port 3001, health check `/health`
- Internet-facing ALB (`devops-g10-iac-alb`) in **≥2 public subnets**
- HTTP listener on port **80** forwarding to the Service A target group

Does not create: Service A / B / C security groups, ECS services, or target registrations. Service A registers into this TG later via `modules/ecs-service` (`enable_alb` + `target_group_arn`). ALB → A on 3001 is enforced on **A’s SG** using output `alb_sg_id` as the source (SG reference, not CIDR).

## Guardrails enforced by the module

- Required tag keys (`Project`, `Group`, `Owner`, `Environment`) must be present.
- `public_subnet_ids` must contain at least two subnets (two AZs).
- Target group `target_type` is hard-coded to `ip` (Fargate `awsvpc`).
- ALB SG does **not** open app ports (3001/3002/3003) to `0.0.0.0/0`.

## Example usage (indicative)

```hcl
module "alb" {
  source = "../../modules/alb"

  vpc_id             = module.network.vpc_id
  public_subnet_ids  = module.network.public_subnet_ids
  container_port     = 3001
  health_check_path  = "/health"

  tags = {
    Project     = "devops-mentorship"
    Group       = "group-10"
    Owner       = "service-a-owner"
    Environment = "lab"
  }
}
```

## Outputs

| Output             | Consumer                                      |
|--------------------|-----------------------------------------------|
| `alb_dns_name`     | Runtime proof / Gate curls                    |
| `target_group_arn` | `ecs-service` instance for Service A          |
| `alb_sg_id`        | Service A SG inbound rule (ALB → A on 3001)   |
