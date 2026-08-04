# 8. State backend design

**Author:** Arsema (Platform)  
**Reviewer:** Berissa  
**Group:** 10 · **Region:** `eu-central-1`

---

## Tooling pins (recorded from kickoff)

| Item | Value |
|---|---|
| Terraform CLI | **v1.15.8** |
| Provider | `hashicorp/aws` **`~> 5.0`** |
| Region | `eu-central-1` |
| Local state as team source of truth | **Forbidden** |

These pins go into `versions.tf` when `infra/` is created. Exact provider patch version is frozen by committing `.terraform.lock.hcl` after first `terraform init`.

---

## Two stacks (must stay separate)

| Stack | Path (planned) | Purpose | Destroy with workload? |
|---|---|---|---|
| **Bootstrap** | `infra/bootstrap/` | Encrypted S3 bucket + locking for Terraform state | **No** — survives forever for the lab |
| **Workload** | `infra/environments/lab/` | VPC, ECS, ALB, services, etc. | **Yes** — every Discover/Teach/Operate destroy |

Backend state for bootstrap is local or a one-time local state that is **not** the team workload state. Workload always uses the remote backend.

---

## Bootstrap requirements (assignment)

When Arsema implements `infra/bootstrap/`, it must create:

| Requirement | How we meet it |
|---|---|
| S3 bucket for state | Name pattern: `devops-g10-tfstate-<account-id>` (or similar unique) |
| Encryption | Bucket default encryption (AES256 or SSE-S3/SSE-KMS) |
| Versioning | Enabled |
| Public access | **Blocked** (all four Block Public Access settings on) |
| State locking | Enabled (S3 native lock and/or DynamoDB lock table — implement per Terraform 1.15 docs we use) |
| Region | `eu-central-1` only |
| Tags | `Project=devops-mentorship`, `Group=group-10`, `Owner=platform-owner`, `Environment=lab` |

---

## Workload backend config (planned shape)

After bootstrap exists, `infra/environments/lab/` will contain something like:

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
    bucket       = "devops-g10-tfstate-<account-id>"  # from bootstrap output
    key          = "lab/workload/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true   # confirm supported flag for our 1.15.8 at implement time
  }
}
```

**Note for implementers:** If `use_lockfile` is not the mechanism in 1.15.8, use the documented locking approach for that version (e.g. DynamoDB table `devops-g10-tf-locks`). Do not bypass locking.

---

## Safety rules

1. Never commit `*.tfstate`, `*.tfstate.*`, `.terraform/`, or saved plan binaries.
2. Never point workload destroy at the bootstrap bucket.
3. Before destroy: confirm account, region, and state **key** in the plan.
4. Console may inspect state bucket / locks; console must not create workload resources.

---

## Evidence for submission

- [ ] Screenshot: bucket versioning + encryption + public access blocked  
- [ ] Screenshot or plan note: locking enabled  
- [ ] PR showing `versions.tf` + committed `.terraform.lock.hcl`  
- [ ] Destroy output showing workload gone while bootstrap bucket remains  
