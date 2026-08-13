# Recovery drill

- **From:** Reliability R3 (Design for recovery)
- **Phase:** 2
- **Status:** Not scheduled

## What
- Rehearse a full restore from WAL archive + basebackup in a throwaway
  environment.
- Time it against RTO ≤ 4h and confirm RPO ≤ 24h.

## Why
- An untested backup is not a backup. Validates RB-16 and the recovery targets
  in `spec.md`.

## Done when
- One drill completed; actual RTO/RPO recorded; gaps fed back into RB-16.
