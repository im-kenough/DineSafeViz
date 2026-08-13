# Failure Mode Analysis (FMA)

- **From:** Reliability R2 (Design for resilience)
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

## Done when
- A table exists mapping failure mode → blast radius → response → recovery.
