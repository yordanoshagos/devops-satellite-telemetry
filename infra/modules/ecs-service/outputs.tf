output "service_name" {
  description = "Name of the created ECS service."
  value       = aws_ecs_service.this.name
}

output "service_arn" {
  description = "ARN of the ECS service."
  value       = aws_ecs_service.this.id
}

output "task_definition_arn" {
  description = "ARN of the registered task definition revision."
  value       = aws_ecs_task_definition.this.arn
}

output "security_group_id" {
  description = "Security group ID for this service (used by other services' ingress_source_sg_ids)."
  value       = aws_security_group.this.id
}

output "log_group_name" {
  description = "CloudWatch log group used by the task."
  value       = aws_cloudwatch_log_group.this.name
}
