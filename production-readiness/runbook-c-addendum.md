# Runbook addendum — Service C (Berissa)

Paste into `production-readiness/runbook.md` under Diagnose / Validate (Arsema owns the full runbook).

## C log group + callback check

**Log group:** `/ecs/devops-g10-iac-anomaly-detector`  
**Service Connect / callback URL expected:** `http://ground-station-api:3001/callback`  
**SG:** anomaly-detector SG → ground-station-api SG on TCP **3001** (callback). Forward A→C must remain denied.

### Diagnose whether C is at fault

```bash
export AWS_PROFILE=g10
export AWS_REGION=eu-central-1

# Is C running?
aws ecs describe-services --cluster devops-g10-iac-cluster \
  --services anomaly-detector \
  --query 'services[].{desired:desiredCount,running:runningCount}' --output table

# Did analyze run? Did callback fail?
aws logs tail /ecs/devops-g10-iac-anomaly-detector --since 30m --format short \
  | grep -E 'analyze_request|anomaly_detection|callback_initiated|callback_sent|ERROR'
```

Interpretation:

| Log pattern | Meaning |
|---|---|
| No recent C logs + running 0 | C down / pull failure — fix C service first |
| `analyze_request` + `anomaly_detection` complete, then `callback_sent` failure | Forward path OK; **callback edge** broken (DNS/SG/URL) |
| `callback_sent` success + A has `callback_received` | C path healthy |

### Mitigate (C-related)

1. If DNS/stale Service Connect: force new deployment on `anomaly-detector` (and A if A DNS also wrong).
2. If SG: restore inbound on A SG from C SG port 3001 — do not open A→C.
3. If bad SHA: set `image_sha_anomaly_detector` to a known-good short SHA, apply, wait for steady state.

### Validate (must prove journey, not only “task running”)

```bash
ALB=http://devops-g10-iac-alb-1207406256.eu-central-1.elb.amazonaws.com
# POST /telemetry → copy processing_request_id → GET /status/<id>
# Success = status completed (and ideally anomaly_status set)
# Also confirm C logs show callback_sent success
```

**Note (Day 0 capture):** baseline showed C analyze OK but callback `NameResolutionError` for `ground-station-api` — treat as open reliability condition until DNS/deploy fix lands. See `alerts/baseline-e2e.txt`.
