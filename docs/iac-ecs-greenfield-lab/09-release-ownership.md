# 9. Application release ownership

## First-release sequence (Cycle 1)

The very first environment build must follow this order — foundation before images, images before services:

```text
1. Apply foundation (bootstrap already applied)
     VPC, subnets, routes, NAT, IAM, cluster, Service Connect namespace, ALB, TG
       ↓
2. Create ECR repositories (A / B / C) via IaC
       ↓
3. Each service owner builds and pushes a sha-<gitsha> image to their ECR repo
       ↓
4. Release owner sets the image_sha_* variables in IaC (PR to develop)
       ↓
5. Plan → review → apply ECS services (task defs, SGs, services, ALB registration for A)
       ↓
6. Runtime proof: Internet → ALB → A → B → C, plus denies
```

Steps 1 and 2 can be a single apply if ECR repos live in the workload stack; otherwise split into two applies.

## Ongoing release contract

```text
App change → tests → build sha-<gitsha> → push ECR
  → update declared image SHA in IaC (tfvars/locals)
  → terraform plan → review → apply
  → ECS rolling deployment
  → new SHA visible through ALB
```

- Image pipeline builds and pushes immutable SHA tags.
- IaC selects which SHA is deployed (no console image edits).
- `latest` is rejected by module variable validation.

## Who does what

| Step | Owner |
|---|---|
| Code change in `service-*` | That service owner |
| Build and push `sha-…` image | That service owner |
| Put SHA into IaC variables | Release owner of the cycle |
| `terraform plan` / `apply` | Cycle operator |
| Prove new SHA via ALB | Release owner + Service A owner |
