# 5. Security-group matrix and traffic contract

## Traffic contract

| Source | Destination | Port | Result |
|---|---|---|---|
| Internet | ALB | 80 | Allow |
| ALB SG | Service A (ground-station-api) | 3001 | Allow |
| Service A SG | Service B (telemetry-parser) | 3002 | Allow |
| Service B SG | Service C (anomaly-detector) | 3003 | Allow |
| Internet | A / B / C directly | any | Deny |
| Service A SG | Service C | 3003 | Deny |
| Service C SG | Service A | 3001 | Allow (documented callback `/callback`) |

## Enforcement rules

- Use **security-group references** only (not task IPs, not `0.0.0.0/0` on app ports).
- Tasks have **no public IPs**; public entry is ALB only.
- Callback C→A is a deliberate app edge (same as console lab); forward path A→C must still deny.

## Per-pair details

| Pair | Dest port | Discovery | Health / path |
|---|---|---|---|
| Internet → ALB | 80 | ALB DNS | — |
| ALB → A | 3001 | TG `ip` | `/health` |
| A → B | 3002 | `service-b` | `/health`, `POST /parse` |
| B → C | 3003 | `service-c` | `/health`, `POST /analyze` |
| C → A callback | 3001 | `service-a` | `/callback` |
