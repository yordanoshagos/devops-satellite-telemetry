# Gate 1 Submission — Draw the Graph (Group 10)

**Group:** group-10  
**Repo:** github.com/yordanoshagos/devops-satellite-telemetry  
**Region:** eu-central-1  
**Phase:** 1 (paper gate; AWS build started in parallel — see checklist below)

Send Rob this **folder** (`docs/ecs-fargate-lab/`):

```
https://github.com/yordanoshagos/devops-satellite-telemetry/tree/main/docs/ecs-fargate-lab
```

## Contents

| File | Gate 1 section |
|------|----------------|
| [01-dependency-graph.md](./01-dependency-graph.md) | Intro, service mapping, §1 Dependency graph, §2 Dependency questions |
| [02-traffic-contracts.md](./02-traffic-contracts.md) | C→A design decision, §4 Traffic contracts (SG matrix + per-pair) |
| [03-failure-predictions.md](./03-failure-predictions.md) | §3 Failure predictions |
| [04-ownership-and-naming.md](./04-ownership-and-naming.md) | §5 Ownership map + expected resource names |
| [scar-log.md](./scar-log.md) | Ongoing failure log (Phases 2–6; grows after Gate 1) |

## Team

| Member | Role |
|--------|------|
| Yordanos | Service A — ground-station-api (3001) |
| Saloi | Service B — telemetry-parser (3002) |
| Berissa | Service C — anomaly-detector (3003) |
| Arsema | Platform — cluster, ALB, namespace, CodeConnections |

## Gate 1 checklist

- [x] Dependency graph → [01-dependency-graph.md](./01-dependency-graph.md)
- [x] Dependency questions → [01-dependency-graph.md](./01-dependency-graph.md)
- [x] Three failure predictions → [03-failure-predictions.md](./03-failure-predictions.md)
- [x] Traffic contracts (SG matrix + per-pair agreements) → [02-traffic-contracts.md](./02-traffic-contracts.md)
- [x] Ownership map → [04-ownership-and-naming.md](./04-ownership-and-naming.md)
- [x] Expected resource names → [04-ownership-and-naming.md](./04-ownership-and-naming.md)
- [x] Team members and platform role assigned
- [x] anomaly-detector → ground-station-api (C → A) decision recorded as deliberate deviation → [02-traffic-contracts.md](./02-traffic-contracts.md)
- [ ] ALB health-check interval/timeout confirmed at deploy time
- [ ] IAM role ARNs recorded once Arsema creates or assigns them
- [ ] Confirm Service Connect names (`service-a/b/c`) vs domain ECR names with instructor if required
- [ ] **Phase 2 started in parallel** — ECR repos, image pushes, and ECS cluster exist before formal Gate 1 review
