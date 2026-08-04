## Card 1 — Two Availability Zones

**Author: Berissa** 

1. **What risk are we reducing?**  
   _TODO_
2. **What trade-off are we accepting?**  
   _TODO_
3. **Which AWS Well-Architected pillar is most relevant?**  
   _TODO_
4. **What evidence will prove the design works?**  
   _TODO_

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

**Author: Saloi** — fill below.

1. **What risk are we reducing?**  
   _TODO_
2. **What trade-off are we accepting?**  
   _TODO_
3. **Which AWS Well-Architected pillar is most relevant?**  
   _TODO_
4. **What evidence will prove the design works?**  
   _TODO_

---

## Card 5 — Remote, versioned and locked state

**Author: Saloi** — fill below.

1. **What risk are we reducing?**  
   _TODO_
2. **What trade-off are we accepting?**  
   _TODO_
3. **Which AWS Well-Architected pillar is most relevant?**  
   _TODO_
4. **What evidence will prove the design works?**  
   _TODO_
