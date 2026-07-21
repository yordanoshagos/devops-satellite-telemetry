# 2. Traffic Contracts

> Part of Gate 1 submission — see [README.md](./README.md) for the full folder index.

---

## Design decision recorded: the anomaly-detector → ground-station-api callback (C → A)

Our design keeps anomaly-detector (C) calling ground-station-api (A) on `/callback`
after analysis completes. The assignment's contract shows only
`Internet → ALB → A → B → C` and states no other path should be permitted, so this
is a **deliberate, documented deviation**, not an oversight.

**Rationale:** it preserves our existing satellite telemetry pipeline and the
order-confirmation behaviour (`processing_request_id` propagates A → B → C → A).
The callback is runtime and best-effort; anomaly-detector does **not** depend on
ground-station-api at startup, so the "no startup cycle" contract still holds.

**What we add to make it defensible:**
- An explicit `anomaly-detector SG → ground-station-api SG` rule on port 3001 (see matrix).
- It is listed in the traffic contract as an intentional extra edge.
- We can defend it in Demo 3 rather than have it read as a broken boundary.

**Grade awareness:** this sits in the "Traffic contracts and security design" band
(10%). It does not break the explicit Gate 2 negative test (which proves A → C
*fails* on the forward path; C → A is a separate direction). Team accepts the
design-band tradeoff.

---

## 4. Traffic contracts

### 4a. Security-group matrix

Base path is `Internet → ALB → ground-station-api → telemetry-parser →
anomaly-detector`. We add one documented extra edge, `anomaly-detector →
ground-station-api` on the `/callback` route.

| Source | Destination | Port | Allowed? | Enforcement |
|---|---|---|---|---|
| Internet | ALB | 80 | Yes | ALB SG inbound `0.0.0.0/0:80` |
| Internet | ground-station-api | 3001 | No | ground-station-api SG has no internet inbound rule |
| Internet | telemetry-parser | 3002 | No | telemetry-parser SG has no internet inbound rule |
| Internet | anomaly-detector | 3003 | No | anomaly-detector SG has no internet inbound rule |
| ALB | ground-station-api | 3001 | Yes | ALB SG reference → ground-station-api SG |
| ground-station-api | telemetry-parser | 3002 | Yes | ground-station-api SG reference → telemetry-parser SG |
| ground-station-api | anomaly-detector | 3003 | No | No matching rule (must fail) |
| telemetry-parser | anomaly-detector | 3003 | Yes | telemetry-parser SG reference → anomaly-detector SG |
| anomaly-detector | ground-station-api | 3001 | Yes (deliberate) | anomaly-detector SG reference → ground-station-api SG (callback) |

Lab note: tasks run in default public subnets with public IPs for **outbound**
access (ECR, CloudWatch). Public IP does not mean publicly reachable; the SG
rules above block all inbound except the permitted paths.

### 4b. Per-pair agreements

| Pair | Protocol | Dest port | Service name | SG reference | Health / path | Timeout |
|---|---|---|---|---|---|---|
| Internet → ALB | HTTP | 80 | ALB public DNS | ALB SG allows `0.0.0.0/0` | n/a | ALB idle 60s (default) |
| ALB → ground-station-api | HTTP | 3001 | ground-station-api | ALB SG → ground-station-api SG | `/health` | health-check interval 30s, timeout 5s (confirm at deploy) |
| ground-station-api → telemetry-parser | HTTP | 3002 | service-b | ground-station-api SG → telemetry-parser SG | `/health`, `POST /parse` | 10s (`requests` default in app) |
| telemetry-parser → anomaly-detector | HTTP | 3003 | service-c | telemetry-parser SG → anomaly-detector SG | `/health`, `POST /analyze` | 10s (`requests` default in app) |
| anomaly-detector → ground-station-api (callback) | HTTP | 3001 | service-a | anomaly-detector SG → ground-station-api SG | `/callback` (target), `/health` | 10s (best-effort) |

Service Connect URLs at Phase 3 (override Compose hostnames via env):

| Caller | URL |
|---|---|
| ground-station-api | `http://service-b:3002/parse` |
| telemetry-parser | `http://service-c:3003/analyze` |
| anomaly-detector | `http://service-a:3001/callback` |
