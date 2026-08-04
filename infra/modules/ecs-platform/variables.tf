variable "cluster_name" {
  description = "Name of the ECS cluster."
  type        = string
  default     = "devops-g10-iac-cluster"
}

variable "service_connect_namespace" {
  description = "Name of the Service Connect (Cloud Map HTTP) namespace used as the cluster default."
  type        = string
  default     = "group10.internal"
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
