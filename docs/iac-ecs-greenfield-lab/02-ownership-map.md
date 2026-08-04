# 2. Ownership map

| Role | Owns in IaC |
|---|---|
| Service A owner | A ECR, module inputs, task def, log group, SG, ECS service, ALB registration, A release evidence |
| Service B owner | B ECR, module inputs, task def, log group, SG, ECS service, B release evidence |
| Service C owner | C ECR, module inputs, task def, log group, SG, ECS service, C release evidence |
| Platform owner | Bootstrap, providers, VPC/network, ECS platform, shared IAM, IaC workflow |
| Release owner | Plan summary, image SHA selection in IaC, runtime release proof, rollback evidence |

Release and platform leads rotate across Discover / Teach / Operate cycles.

## Rules

- Owner types; team observes; operator narrates; coach asks questions; evidence decides.
- No one takes over another engineer’s terminal during a cycle or demo.
- One apply operator at a time.
- Old console cluster `devops-g10-cluster` is not modified by IaC.
