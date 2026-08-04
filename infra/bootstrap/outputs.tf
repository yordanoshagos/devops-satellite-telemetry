output "state_bucket_name" {
  description = "S3 bucket for Terraform remote state. Use as backend.bucket in downstream stacks."
  value       = aws_s3_bucket.tfstate.bucket
}

output "state_bucket_region" {
  description = "Region the state bucket lives in."
  value       = "eu-central-1"
}
