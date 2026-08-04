output "cluster_id" {
  description = "ID of the ECS cluster."
  value       = aws_ecs_cluster.this.id
}

output "cluster_arn" {
  description = "ARN of the ECS cluster."
  value       = aws_ecs_cluster.this.arn
}

output "cluster_name" {
  description = "Name of the ECS cluster."
  value       = aws_ecs_cluster.this.name
}

output "service_connect_namespace_arn" {
  description = "ARN of the Service Connect (Cloud Map HTTP) namespace."
  value       = aws_service_discovery_http_namespace.this.arn
}

output "service_connect_namespace_name" {
  description = "Name of the Service Connect namespace, e.g. group10.internal."
  value       = aws_service_discovery_http_namespace.this.name
}

output "execution_role_arn" {
  description = "ARN of the shared ECS task execution role (ECR pull, CloudWatch Logs)."
  value       = aws_iam_role.execution.arn
}

output "task_role_arn" {
  description = "ARN of the shared ECS task role (application-level permissions)."
  value       = aws_iam_role.task.arn
}
