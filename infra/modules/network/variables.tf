variable "name_prefix" {
  description = "Prefix applied to VPC, subnets, IGW, NAT, and route tables (e.g. devops-g10-iac-)."
  type        = string
  default     = "devops-g10-iac-"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.10.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 CIDR."
  }
}

variable "availability_zones" {
  description = "AZs for the two public + two private subnets. Order maps 1:1 to *_subnet_cidrs."
  type        = list(string)
  default     = ["eu-central-1a", "eu-central-1b"]

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "This module expects exactly two AZs."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDRs for the two public subnets (index 0 → AZ index 0)."
  type        = list(string)
  default     = ["10.10.0.0/24", "10.10.1.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Provide exactly two public subnet CIDRs."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDRs for the two private (app) subnets (index 0 → AZ index 0)."
  type        = list(string)
  default     = ["10.10.10.0/24", "10.10.11.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Provide exactly two private subnet CIDRs."
  }
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
