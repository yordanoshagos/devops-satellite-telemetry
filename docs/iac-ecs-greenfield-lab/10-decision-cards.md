## Card 1 — Two Availability Zones


1. **What risk are we reducing?**  
   Single-AZ outage taking down ALB or all tasks; no place for A’s second task.

2. **What trade-off are we accepting?**  
   Slightly higher cost (ALB across 2 AZs, more subnets); more resources to manage.

3. **Which AWS Well-Architected pillar is most relevant?**  
   Reliability.
4. **What evidence will prove the design works?**  
   ALB subnets in two AZs; Service A tasks placed in two AZs; TG healthy across AZs.

---

## Card 2 — Private Fargate tasks 

1. **What risk are we reducing?**  
   Tasks are not reachable from the Internet even if a security-group mistake is made later. We remove accidental public exposure of application ports 3001/3002/3003 and force all ingress through the ALB path we control.

2. **What trade-off are we accepting?**  
   Private tasks need explicit egress (we chose a NAT Gateway). That adds hourly cost and another dependency: if NAT or private routes break, tasks cannot pull images or write logs. First apply is slightly slower to design than “public IP on tasks.”

3. **Which AWS Well-Architected pillar is most relevant?**  
   **Security** (least privilege network exposure). Reliability is secondary (placement still spans two private AZs).

4. **What evidence will prove the design works?**  
   - ECS task ENIs show no public IP.  
   - Internet → task ENI/app port denied; Internet → ALB :80 allowed.  
   - Tasks still reach `RUNNING` (ECR pull via NAT) and CloudWatch logs appear.  
   - Route table on private subnets: `0.0.0.0/0` → NAT.

---

## Card 3 — Security-group references instead of IP allowlists

1. **What risk are we reducing?**  
   **Risk reduced:** Brittle allowlists on task IPs that break on every replace; accidental wide-open `0.0.0.0/0` on app ports.
2. **What trade-off are we accepting?**  
   **Trade-off:** SG rules are coupled (order/dependencies in Terraform); harder to “just open a port” for quick debug.
3. **Which AWS Well-Architected pillar is most relevant?**  
   **Pillar:** Security.
4. **What evidence will prove the design works?**  
   **Evidence:** SG rules show source = other SG IDs; allow A→B and B→C; deny A→C and Internet→tasks; runtime proof matches.

---

## Card 4 — Immutable image SHA



1. **What risk are we reducing?**  
   Mystery deploys and floating `latest` retags — we always know which Git commit is running in ECS.
2. **What trade-off are we accepting?**  
   Every release needs a build/push plus an IaC SHA update; slightly more steps than a floating tag.
3. **Which AWS Well-Architected pillar is most relevant?**  
   **Operational Excellence** (controlled, repeatable releases).
4. **What evidence will prove the design works?**  
   - Variable validation / tests reject `latest`.  
   - Task definition and runtime show `sha-<gitsha>`.  
   - After apply, ALB serves that same SHA.

---

## Card 5 — Remote, versioned and locked state



1. **What risk are we reducing?**  
   Local state divergence, lost state, and two people applying at once overwriting each other.
2. **What trade-off are we accepting?**  
   A bootstrap stack must exist and stay protected; extra setup before the first workload apply.
3. **Which AWS Well-Architected pillar is most relevant?**  
   **Operational Excellence** / **Reliability**.
4. **What evidence will prove the design works?**  
   - S3 backend with versioning, encryption, and public access blocked.  
   - Lock prevents concurrent apply.  
   - Destroy removes workload but not the bootstrap bucket.
