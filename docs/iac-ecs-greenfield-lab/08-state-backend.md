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
| Bootstrap | `infra/bootstrap/` | Encrypted S3 bucket for state + locking | **No** |
| Workload | `infra/environments/lab/` | VPC, ECS, ALB, services | **Yes** |

## Locking decision (chosen)

We use the **S3 native lockfile** (`use_lockfile = true`) supported by Terraform 1.15.8. We do **not** create a DynamoDB lock table.

- Simpler: no extra resource; the lock lives inside the same S3 bucket.
- No unresolved implementation choice at apply time.
- If a future Terraform upgrade removes or changes this flag, the platform owner will migrate to DynamoDB in one dedicated PR — not silently.

## Bootstrap bucket requirements

| Requirement | Value |
|---|---|
| Name | `devops-g10-tfstate-<account-id>` |
| Encryption | Default (AES256 / SSE-S3) |
| Versioning | Enabled |
| Public access | Blocked |
| Locking | **S3 lockfile** (`use_lockfile = true`) |
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

## Safety

- Never commit state, `.terraform/`, or saved plans.
- Never destroy the bootstrap bucket with the workload.
- Before destroy: confirm account, region, and state key.
- Console may inspect; console must not create IaC-managed resources.
