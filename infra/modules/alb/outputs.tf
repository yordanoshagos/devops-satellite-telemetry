output "alb_dns_name" {
  description = "Public DNS name of the internet-facing ALB (use for /health and E2E curls)."
  value       = aws_lb.this.dns_name
}

output "target_group_arn" {
  description = "ARN of the IP-type target group for Service A. Pass to ecs-service when enable_alb is true."
  value       = aws_lb_target_group.service_a.arn
}

output "alb_sg_id" {
  description = "ALB security group ID. Service A SG must allow inbound container_port from this SG."
  value       = aws_security_group.alb.id
}

output "alb_arn" {
  description = "ARN of the application load balancer."
  value       = aws_lb.this.arn
}

output "listener_arn" {
  description = "ARN of the HTTP :80 listener."
  value       = aws_lb_listener.http.arn
}
