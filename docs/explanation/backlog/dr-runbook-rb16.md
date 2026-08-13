# DR activation runbook (RB-16)

- **From:** Reliability R3 (Design for recovery)
- **Checklist item:** [RE:09](https://learn.microsoft.com/en-us/azure/well-architected/reliability/disaster-recovery) — Implement structured, tested, documented DR plans.
- **Phase:** 2
- **Status:** Named in spec, not written

## What
- Step-by-step runbook to activate the passive-cold DR region.
- Cover: provision from IaC, restore Postgres from WAL archive, repoint DNS,
  validate, and fail back.

## Why
- The DR pattern is designed but unusable under pressure without a tested
  procedure. Meets RTO ≤ 4h only if the steps are known.

## Guidance ([RE:09](https://learn.microsoft.com/en-us/azure/well-architected/reliability/disaster-recovery))
- Define **disaster thresholds / activation criteria** — what counts as a
  disaster vs. a minor incident.
- Document roles, communication + escalation paths, and a decision owner.
- Write ordered steps with all prerequisites (scripts, credentials, configs):
  provision secondary from IaC → restore Postgres from WAL → repoint DNS →
  validate.
- Keep **failback** a separate, documented process — not an afterthought.
- Store the runbook + DR assets (credentials, certs) in a highly-available
  location reachable during a regional outage; predeploy CI/CD in the DR region.
- Keep it aligned with the FMA; review ~every 6 months; validate via the drill.

## Done when
- RB-16 is written and validated by the recovery drill.
