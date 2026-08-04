# 8. State backend

## Tooling (from kickoff)

| Item | Value |
|---|---|
| Terraform CLI | v1.15.8 |
| Provider | `hashicorp/aws` `~> 5.0` |
| Region | `eu-central-1` |
| Local state as team source of truth | Forbidden |

Pins go in `versions.tf`. Exact provider version frozen by committing `.terraform.lock.hcl` after first `terraform init`.

## Two stacks

| Stack | Path | Purpose | Destroy with workload? |
|---|---|---|---|
| Bootstrap | `infra/bootstrap/` | Encrypted S3 + locking for state | **No** |
| Workload | `infra/environments/lab/` | VPC, ECS, ALB, services | **Yes** |

## Bootstrap bucket requirements

| Requirement | Value |
|---|---|
| Name | `devops-g10-tfstate-<account-id>` |
| Encryption | Default (AES256 / SSE-S3) |
| Versioning | Enabled |
| Public access | Blocked |
| Locking | Enabled (S3 lock and/or DynamoDB `devops-g10-tf-locks`) |
| Region | `eu-central-1` |
| Tags | `Project=devops-mentorship`, `Group=group-10`, `Owner=platform-owner`, `Environment=lab` |

## Workload backend (planned)

```hcl
terraform {
  required_version = ">= 1.15.8, < 1.16.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket       = "devops-g10-tfstate-<account-id>"
    key          = "lab/workload/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}
```

If `use_lockfile` is not available on 1.15.8, use the documented lock approach for that version. Do not bypass locking.

## Safety

- Never commit state, `.terraform/`, or saved plans.
- Never destroy the bootstrap bucket with the workload.
- Before destroy: confirm account, region, and state key.
- Console may inspect; console must not create IaC-managed resources.
