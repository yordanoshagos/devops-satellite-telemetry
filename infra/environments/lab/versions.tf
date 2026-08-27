terraform {
  required_version = ">= 1.15.8, < 1.16.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # backend blocks can't use variables, so the bootstrap bucket name is literal.
  # See infra/bootstrap/ and docs/iac-ecs-greenfield-lab/08-state-backend.md.
  backend "s3" {
    bucket       = "devops-g10-tfstate-240462142849"
    key          = "lab/workload/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region
}
