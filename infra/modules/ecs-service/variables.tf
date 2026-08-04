variable "name" {
  description = "Application/container name, e.g. ground-station-api. Also used as the ECS service and task-def family name (prefixed elsewhere)."
  type        = string

  validation {
    condition     = length(var.name) > 0 && length(var.name) <= 60
    error_message = "name must be 1..60 characters."
  }
}

variable "name_prefix" {
  description = "Prefix applied to task-def family, log group, and SG name (e.g. devops-g10-)."
  type        = string
  default     = "devops-g10-"
}

variable "service_connect_name" {
  description = "Discovery name used inside the Service Connect namespace (e.g. service-a, service-b, service-c). Also used as the container port mapping name."
  type        = string
}

variable "container_port" {
  description = "TCP port the container listens on."
  type        = number

  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535
    error_message = "container_port must be between 1 and 65535."
  }
}

variable "image" {
  description = "Full container image URI. Must be an immutable sha-... tag; :latest is rejected."
  type        = string

  validation {
    condition     = !endswith(lower(var.image), ":latest") && !strcontains(lower(var.image), ":latest ")
    error_message = "image must not use the :latest tag."
  }

  validation {
    condition     = can(regex(":sha-[0-9a-f]{7,40}$", var.image)) || can(regex("@sha256:[0-9a-f]{64}$", var.image))
    error_message = "image tag must be sha-<gitsha> or a @sha256:<digest> reference."
  }
}

variable "desired_count" {
  description = "Number of running tasks."
  type        = number
  default     = 1

  validation {
    condition     = var.desired_count >= 1 && var.desired_count <= 10
    error_message = "desired_count must be between 1 and 10 for this lab."
  }
}

variable "cpu" {
  description = "Fargate CPU units."
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate memory in MiB."
  type        = number
  default     = 512
}

variable "cluster_arn" {
  description = "ECS cluster ARN this service runs in."
  type        = string
}

variable "service_connect_namespace_arn" {
  description = "Cloud Map namespace ARN used by ECS Service Connect (e.g. group10.internal)."
  type        = string
}

variable "task_execution_role_arn" {
  description = "IAM role ARN ECS uses to pull the image and write logs."
  type        = string
}

variable "task_role_arn" {
  description = "IAM role ARN the container assumes at runtime (used for ECS Exec)."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs where Fargate tasks are placed (2+ AZs)."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "Provide at least two private subnets for AZ spread."
  }
}

variable "vpc_id" {
  description = "VPC ID the service security group belongs to."
  type        = string
}

variable "ingress_source_sg_ids" {
  description = "Security group IDs that are allowed to reach this service on container_port. Use SG references only, never CIDRs."
  type        = list(string)
  default     = []
}

variable "enable_alb" {
  description = "Attach this service to an ALB target group (Service A only)."
  type        = bool
  default     = false
}

variable "alb_target_group_arn" {
  description = "Target group ARN to attach when enable_alb = true."
  type        = string
  default     = null
}

variable "alb_security_group_id" {
  description = "ALB security group ID that is allowed inbound on container_port when enable_alb = true."
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "CloudWatch log retention (days)."
  type        = number
  default     = 7
}

variable "enable_execute_command" {
  description = "Enable ECS Exec on the service (required by the assignment)."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to every resource in this module. Must include Project, Group, Owner, Environment."
  type        = map(string)

  validation {
    condition = alltrue([
      contains(keys(var.tags), "Project"),
      contains(keys(var.tags), "Group"),
      contains(keys(var.tags), "Owner"),
      contains(keys(var.tags), "Environment"),
    ])
    error_message = "tags must include Project, Group, Owner, and Environment."
  }
}
