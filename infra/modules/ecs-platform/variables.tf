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
  description = "Tags applied to all resources created by this module."
  type        = map(string)
  default     = {}
}
