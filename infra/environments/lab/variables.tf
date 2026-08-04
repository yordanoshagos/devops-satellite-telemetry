variable "region" {
  description = "AWS region. Locked to eu-central-1 per kickoff decision 1."
  type        = string
  default     = "eu-central-1"

  validation {
    condition     = var.region == "eu-central-1"
    error_message = "This lab is scoped to eu-central-1 only (see docs/iac-ecs-greenfield-lab/00-kickoff-decisions.md)."
  }
}

variable "tags" {
  description = "Base tags (Project, Group, Owner, Environment). Owner defaults to platform-owner for shared infra (network, ecs-platform, alb); service modules override it to service-a/b/c-owner per docs/iac-ecs-greenfield-lab/06-names-and-tags.md."
  type        = map(string)

  default = {
    Project     = "devops-mentorship"
    Group       = "group-10"
    Owner       = "platform-owner"
    Environment = "lab"
  }

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

variable "image_sha_ground_station_api" {
  description = "Git short SHA for the ground-station-api image. Composed into devops-g10-ground-station-api:sha-<value>. No default — always supplied by CI, never latest."
  type        = string
}

variable "image_sha_telemetry_parser" {
  description = "Git short SHA for the telemetry-parser image. Composed into devops-g10-telemetry-parser:sha-<value>."
  type        = string
}

variable "image_sha_anomaly_detector" {
  description = "Git short SHA for the anomaly-detector image. Composed into devops-g10-anomaly-detector:sha-<value>."
  type        = string
}
