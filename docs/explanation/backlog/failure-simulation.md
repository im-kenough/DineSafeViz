# Failure simulation

- **From:** Reliability R4 (Design for operations)
- **Phase:** 3
- **Status:** Undecided

## What
- Decide whether to run controlled failure/chaos tests (kill a pod/node, expire
  a cert, cut the ETL feed) in staging.
- Pick a lightweight approach if adopted (manual scripts likely enough).

## Why
- Confirms self-healing and alerts behave as designed under real fault
  conditions.

## Done when
- Decision recorded; if adopted, one scenario run in staging.
