# RE:08 — Recovery drill

- **From:** Reliability R3 (Design for recovery)
- **Checklist item:** [RE:08](https://learn.microsoft.com/en-us/azure/well-architected/reliability/reliability-test) — Test for resiliency/recovery scenarios (backup & restore).
- **Phase:** 2
- **Status:** Not scheduled

## What
- Rehearse a full restore from WAL archive + basebackup in a throwaway
  environment.
- Time it against RTO ≤ 4h and confirm RPO ≤ 24h.

## Why
- An untested backup is not a backup. Validates RB-16 and the recovery targets
  in `spec.md`.

## Guidance ([RE:08](https://learn.microsoft.com/en-us/azure/well-architected/reliability/reliability-test))
- Test the restore in an **isolated** (non-prod) environment first — never first
  in production.
- Validate data **integrity and completeness**, not just that the restore
  succeeds.
- Measure actual RTO/RPO against the targets in [spec.md](../../ref/spec.md);
  analyze any gap and feed it back into RB-16.
- Run a **tabletop exercise** first to rehearse roles, then a real restore.
- Set a cadence tied to how often backup config, schema, or infra changes.

## Done when
- One drill completed; actual RTO/RPO recorded; gaps fed back into RB-16.
