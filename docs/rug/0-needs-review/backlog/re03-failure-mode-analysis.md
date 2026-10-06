# RE:03 — Failure Mode Analysis (FMA)

- **From:** Reliability R2 (Design for resilience)
- **Checklist item:** [RE:03](https://learn.microsoft.com/en-us/azure/well-architected/reliability/failure-mode-analysis) — Use failure mode analysis to identify potential failures.
- **Phase:** 1 (design task)
- **Status:** Not started

## What
- List each failure mode per critical component (Postgres pod, node, zone,
  region, ingress, PVC, cert expiry).
- Rate each by risk and impact.
- Record the detection + recovery mechanism for each.

## Why
- Confirms the self-healing / passive-cold design actually covers the failures
  that matter before implementation.

## Guidance ([RE:03](https://learn.microsoft.com/en-us/azure/well-architected/reliability/failure-mode-analysis))
- Decompose the workload into components: ingress, compute, data, storage,
  secrets, egress.
- Overlay the critical flows (A/B) onto those components using flow criticality.
- Identify internal + external dependencies; classify each **strong** or **weak**.
- For each component, evaluate failure modes: zone/region outage, service
  outage, misconfiguration, operator error, planned maintenance, overload —
  consider read vs. write separately.
- For each, plan a **mitigation** (add resiliency *or* degrade gracefully) and a
  **detection** (monitoring/alert).
- Record in a table: component | risk | likelihood | effect/mitigation | outage.
  Prioritize by severity × likelihood; revisit as the design changes.

## Done when
- A table exists mapping failure mode → blast radius → response → recovery.
