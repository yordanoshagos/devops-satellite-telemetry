# 9. Application release ownership

## Contract

```text
App change → tests → build sha-<gitsha> → push ECR
  → update declared image SHA in IaC (tfvars/locals)
  → terraform plan → review → apply
  → ECS rolling deployment
  → new SHA visible through ALB
```
- Image pipeline builds and pushes immutable SHA tags.
- IaC selects which SHA is deployed (no console image edits).
- latest is rejected.
