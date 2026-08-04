# Gate 0 / Kickoff decisions

## Decision 1 — Tooling

| Item | Value |
|---|---|
| IaC tool | **Terraform** (not OpenTofu) |
| Terraform CLI | **v1.15.8** (everyone installs this exact version) |
| AWS provider source | `hashicorp/aws` |
| AWS provider version pin | `~> 5.0` |
| Lockfile | After first `terraform init`, commit `.terraform.lock.hcl` |
| AWS Region | `eu-central-1` only |

**Will live in code later (not yet created):** `infra/bootstrap/versions.tf` and `infra/environments/lab/versions.tf`:

```hcl
terraform {
  required_version = ">= 1.15.8, < 1.16.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}
```


## Decision 2 — Network

| Item | Value |
|---|---|
| VPC CIDR | `10.10.0.0/16` |
| Public subnet AZ-1 (`eu-central-1a`) | `10.10.0.0/24` |
| Public subnet AZ-2 (`eu-central-1b`) | `10.10.1.0/24` |
| Private app subnet AZ-1 | `10.10.10.0/24` |
| Private app subnet AZ-2 | `10.10.11.0/24` |
| Egress for private Fargate | **NAT Gateway** (one NAT in a public subnet for the lab) |
| Task public IPs | **false** (`assign_public_ip = false`) |
| ALB | Internet-facing, spans both public subnets |
