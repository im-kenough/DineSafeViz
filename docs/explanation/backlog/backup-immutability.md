# Backup immutability

- **From:** Reliability R3 (Design for recovery)
- **Phase:** 1 (decision)
- **Status:** Undecided

## What
- Decide whether WAL/basebackup blobs get an immutable (WORM) storage policy.
- If yes, set a retention window on the backup storage account/container.

## Why
- Protects backups from accidental or malicious deletion/tampering — the
  integrity half of a trustworthy recovery point.

## Done when
- Decision recorded (adopt WORM + window, or accept the risk with rationale).
