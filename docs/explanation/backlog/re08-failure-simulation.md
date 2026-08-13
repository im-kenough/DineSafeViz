# RE:08 — Failure simulation

- **From:** Reliability R4 (Design for operations)
- **Checklist item:** [RE:08](https://learn.microsoft.com/en-us/azure/well-architected/reliability/reliability-test) — Apply chaos engineering principles.
- **Phase:** 3
- **Status:** Undecided

## What
- Decide whether to run controlled failure/chaos tests (kill a pod/node, expire
  a cert, cut the ETL feed) in staging.
- Pick a lightweight approach if adopted (manual scripts likely enough).

## Why
- Confirms self-healing and alerts behave as designed under real fault
  conditions.

## Guidance ([RE:08](https://learn.microsoft.com/en-us/azure/well-architected/reliability/reliability-test))
- Each experiment targets a specific fault with a clear **hypothesis** (e.g.
  "killing the Postgres pod recovers within RTO tier 1").
- Use the FMA to focus experiments on the highest impact × likelihood failures.
- **Contain blast radius**: target components you can recover quickly; be ready
  to stop and roll back.
- Start in non-production; measure degraded metrics against baselines.
- Feed results back into tests, recovery plans, and the backlog.
- Azure option: Azure Chaos Studio (or simple manual `kubectl`/CLI scripts at
  this scale).

## Done when
- Decision recorded; if adopted, one scenario run in staging.
