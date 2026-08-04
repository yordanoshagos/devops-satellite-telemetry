variable "name_prefix" {
  description = "Prefix applied to ALB, target group, and ALB security group (e.g. devops-g10-iac-)."
  type        = string
  default     = "devops-g10-iac-"
}

variable "vpc_id" {
  description = "VPC ID where the ALB, target group, and ALB SG are created."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the internet-facing ALB. Must span at least two AZs."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_ids) >= 2
    error_message = "ALB must be placed in at least two public subnets (two AZs)."
  }
}

variable "container_port" {
  description = "Service A container port registered on the target group (ground-station-api)."
  type        = number
  default     = 3001

  validation {
    condition     = var.container_port > 0 && var.container_port <= 65535
    error_message = "container_port must be a valid TCP port."
  }
}

variable "health_check_path" {
  description = "HTTP health-check path for the Service A target group."
  type        = string
  default     = "/health"
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
