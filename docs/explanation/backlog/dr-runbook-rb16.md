# DR activation runbook (RB-16)

- **From:** Reliability R3 (Design for recovery)
- **Phase:** 2
- **Status:** Named in spec, not written

## What
- Step-by-step runbook to activate the passive-cold DR region.
- Cover: provision from IaC, restore Postgres from WAL archive, repoint DNS,
  validate, and fail back.

## Why
- The DR pattern is designed but unusable under pressure without a tested
  procedure. Meets RTO ≤ 4h only if the steps are known.

## Done when
- RB-16 is written and validated by the recovery drill.
