# 5. Security-group matrix and traffic contract

Security groups in AWS have no explicit deny. A path is “denied” **only because no allow rule exists** for it. We express that below with **Result** (behaviour) and **Enforcement** (what actually exists in the rule set).

## Traffic contract

| Source | Destination | Port | Result | Enforcement |
|---|---|---|---|---|
| Internet | ALB | 80 | Allow | ALB SG inbound `0.0.0.0/0:80` |
| ALB SG | Service A (ground-station-api) | 3001 | Allow | A SG inbound: source = ALB SG |
| Service A SG | Service B (telemetry-parser) | 3002 | Allow | B SG inbound: source = A SG |
| Service B SG | Service C (anomaly-detector) | 3003 | Allow | C SG inbound: source = B SG |
| Internet | A / B / C directly | any | Denied | No inbound rule from `0.0.0.0/0` on task SGs; tasks have no public IPs |
| Service A SG | Service C | 3003 | Denied | **No rule** on C SG that allows source = A SG |
| Service C SG | Service A | 3001 | Allow (callback `/callback`) | A SG inbound: source = C SG |

## Enforcement rules

- Use **security-group references** only (no task IPs, no `0.0.0.0/0` on app ports).
- Tasks have **no public IPs**; public entry is via the ALB only.
- Denies are the absence of an allow rule — do not add explicit deny rules (SGs do not support them).
- Callback C→A is a deliberate app edge; forward A→C remains denied (no allow rule).

## Per-pair details

| Pair | Dest port | Discovery | Health / path |
|---|---|---|---|
| Internet → ALB | 80 | ALB DNS | — |
| ALB → A | 3001 | TG type `ip` | `/health` |
| A → B | 3002 | `service-b` | `/health`, `POST /parse` |
| B → C | 3003 | `service-c` | `/health`, `POST /analyze` |
| C → A callback | 3001 | `service-a` | `/callback` |
