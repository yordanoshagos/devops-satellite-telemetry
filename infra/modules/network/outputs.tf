output "vpc_id" {
  description = "ID of the created VPC."
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "IDs of the two public subnets (ordered to match availability_zones)."
  value       = [for k in ["a", "b"] : aws_subnet.public[k].id]
}

output "private_subnet_ids" {
  description = "IDs of the two private subnets (ordered to match availability_zones)."
  value       = [for k in ["a", "b"] : aws_subnet.private[k].id]
}
