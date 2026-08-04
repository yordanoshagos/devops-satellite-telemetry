# module `ecs-platform`

Shared ECS platform for the three greenfield services (A / B / C).

Creates:

- ECS cluster (`devops-g10-iac-cluster`)
- Service Connect (Cloud Map HTTP) namespace (`group10.internal`), set as the cluster's default namespace
- Shared execution role (ECR pull + CloudWatch Logs, via `AmazonECSTaskExecutionRolePolicy`)
- Shared task role, with an inline policy granting ECS Exec (`ssmmessages:CreateControlChannel`, `CreateDataChannel`, `OpenControlChannel`, `OpenDataChannel`) — `ecs-service` enables Exec by default, so this is required for any service to start a session

Does not create: VPC/subnets, ALB, ECS services, or ECR repositories. Those live in `network`, `alb`, and `ecs-service`.

## Guardrails enforced by the module

- Required tag keys (`Project`, `Group`, `Owner`, `Environment`) must be present.
- Task role carries only the ECS Exec permission — no other app-level permissions. Service-specific permissions, if ever needed, get added per service, not here.

## Example usage (indicative)

```hcl
module "platform" {
  source = "../../modules/ecs-platform"

  tags = local.tags
}
```

## Outputs

| Output                           | Consumer                                    |
|-----------------------------------|----------------------------------------------|
| `cluster_arn`                    | `ecs-service` (`cluster_arn`)                |
| `cluster_id` / `cluster_name`    | reference / console lookups                  |
| `service_connect_namespace_arn`  | `ecs-service` (`service_connect_namespace_arn`) |
| `service_connect_namespace_name` | reference                                    |
| `execution_role_arn`             | `ecs-service` (`task_execution_role_arn`)    |
| `task_role_arn`                  | `ecs-service` (`task_role_arn`)              |
