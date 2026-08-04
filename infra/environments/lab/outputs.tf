output "alb_dns_name" {
  description = "Public DNS name of the ALB. Use for /health and E2E curls."
  value       = module.alb.alb_dns_name
}

output "cluster_name" {
  description = "Name of the ECS cluster."
  value       = module.platform.cluster_name
}

output "ecr_repository_urls" {
  description = "ECR repository URLs, keyed by app name, for CI image pushes."
  value = {
    "ground-station-api" = aws_ecr_repository.ground_station_api.repository_url
    "telemetry-parser"   = aws_ecr_repository.telemetry_parser.repository_url
    "anomaly-detector"   = aws_ecr_repository.anomaly_detector.repository_url
  }
}

output "vpc_id" {
  description = "VPC ID for the lab environment."
  value       = module.network.vpc_id
}
