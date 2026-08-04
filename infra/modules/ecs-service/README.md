# module `ecs-service`

Reusable Fargate service used three times (A / B / C).

Creates, for one service:

- CloudWatch log group
- Security group (own SG for this service)
- Security-group ingress rules from a list of source SGs (references only, no CIDRs)
- Task definition (Fargate, `awsvpc`, named container port for Service Connect)
- ECS service (Fargate, private subnets, `assign_public_ip = false`, deployment circuit breaker + rollback, ECS Exec, Service Connect client + optional server side)
- Optional ALB target-group attachment (Service A only)

Does not create: cluster, Service Connect namespace, IAM roles, ECR repositories, or the ALB itself. Those live in `ecs-platform` and `alb`.

## Guardrails enforced by the module

- Image tag must be an immutable `sha-…` reference — `latest` is rejected.
- Fargate tasks always run with `assign_public_ip = false`.
- Required tag keys (`Project`, `Group`, `Owner`, `Environment`) must be present.
- Port and desired-count bounds are validated.

## Example usage (indicative)

```hcl
module "service_b" {
  source = "../../modules/ecs-service"

  name                 = "telemetry-parser"
  service_connect_name = "service-b"
  container_port       = 3002
  desired_count        = 1

  image = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com/devops-g10-telemetry-parser:sha-${var.sha_service_b}"

  cluster_arn                     = module.platform.cluster_arn
  service_connect_namespace_arn   = module.platform.namespace_arn
  task_execution_role_arn         = module.platform.execution_role_arn
  task_role_arn                   = module.platform.task_role_arn

  private_subnet_ids   = module.network.private_subnet_ids
  ingress_source_sg_ids = [module.service_a.security_group_id]

  tags = local.tags
}
```
