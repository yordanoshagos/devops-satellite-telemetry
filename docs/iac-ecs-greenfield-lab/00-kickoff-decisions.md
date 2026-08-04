# Gate 0 / Kickoff decisions 

**Author:** Arsema (Platform)  
**Group:** 10  
**When:** Tuesday 4 August 2026 — group locked these together before Gate 1 docs

Everyone replies ✅ in chat. Arsema records the final text **here**. This file is the paper trail for trainers.

---

## Decision 1 — Tooling (LOCKED)

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

**Team sign-off**

| Person | ✅ |
|---|---|
| Arsema | |
| Yordanos | |
| Saloi | |
| Berissa | |

---

## Decision 2 — Network (LOCKED)

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

Berissa expands capacity/headroom in `03-cidr-subnet-capacity.md`.  
Arsema expands routes in `04-routes-egress.md`.

**Team sign-off**

| Person | ✅ |
|---|---|
| Arsema | |
| Yordanos | |
| Saloi | |
| Berissa | |

---

## Decision 3 — Gate 1 owners + deadline (LOCKED)

**Deadline for Gate 1 markdown:** today **13:00**  
**Peer review done by:** today **14:00**  
**Workload apply unlocked only after:** checklist below is all ✅

| Doc | Owner | Reviewer |
|---|---|---|
| `00-kickoff-decisions.md` | Arsema | All |
| `01-dependency-graph.md` | Arsema | Yordanos |
| `02-ownership-map.md` | Saloi | Berissa |
| `03-cidr-subnet-capacity.md` | Berissa | Arsema |
| `04-routes-egress.md` | Arsema | Saloi |
| `05-sg-matrix-traffic.md` | Yordanos | Saloi |
| `06-names-and-tags.md` | Saloi | Berissa |
| `07-failure-predictions.md` | Berissa | Yordanos |
| `08-state-backend.md` | Arsema | Berissa |
| `09-release-ownership.md` | Yordanos | Berissa |
| `10-decision-cards.md` | Split (see that file) | Pair reviewers |

**Team sign-off**

| Person | ✅ |
|---|---|
| Arsema | |
| Yordanos | |
| Saloi | |
| Berissa | |

---

## Decision 4 — Safety red lines (LOCKED)

- ❌ No `terraform apply` for VPC / ECS / ALB / services until Gate 1 checklist is green.
- ✅ Allowed before unlock: install Terraform 1.15.8, write these docs, draft `.tf` on branches.
- ❌ Do **not** destroy or modify the old console lab cluster `devops-g10-cluster` or its ALB/SGs.
- ✅ IaC creates a **new** cluster: `devops-g10-iac-cluster` (and new VPC/ALB names with `-iac-`).
- ❌ No credentials, state files, or secret tfvars in Git.
- ❌ Work only in `eu-central-1`.

**Team sign-off**

| Person | ✅ |
|---|---|
| Arsema | |
| Yordanos | |
| Saloi | |
| Berissa | |

---

## Gate 1 completion checklist (unlock apply)

- [ ] Kickoff decisions 1–4 signed
- [ ] Dependency graph + ownership map
- [ ] CIDR + subnet capacity (rolling headroom)
- [ ] Route table + egress design
- [ ] SG matrix + traffic contract
- [ ] Expected names + tags
- [ ] Three failure predictions
- [ ] State-backend design
- [ ] Release ownership (SHA pipeline vs IaC select)
- [ ] Five architecture decision cards
- [ ] Peer review done (14:00)

**Apply unlocked by (name + time):** _______________________
