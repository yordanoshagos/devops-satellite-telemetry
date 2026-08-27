# SLO review note — Berissa (Service C)

Reviewed proposed SLIs/SLOs in `reliability-target.md` (when present) against what Service C can support.

## Position

- **Availability via ALB `/health`:** necessary but **not sufficient**. `/health` can be `operational` with B reachable while C→A callback is broken (seen 2026-08-28). Do not score the critical journey green on `/health` alone.
- **Success/correctness = % reaching `completed`:** **agree — keep or tighten.** This is the only SLI that includes C’s callback. C owner depends on this.
- **Latency p95 < 2s end-to-end:** OK as a starting SLO if “end-to-end” means accept → **completed**. If measured only to A’s HTTP response for `POST /telemetry` (202 accepted), it **hides** callback failures and under-states user wait.
- **What B/C can support:** C is desired count **1** (no redundancy). A C task stop burns availability/success budget immediately. Single-NAT egress failures also block C pulls. SLOs are aspirational until callback DNS/SG is stable on every deploy.

## Vote on targets

Approve success-rate SLI as written; request explicit wording that **completed status** (not ALB 200) is the correctness signal. Flag current callback DNS failure as a **GO WITH CONDITIONS** item until fixed.
