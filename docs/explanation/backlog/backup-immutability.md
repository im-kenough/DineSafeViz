# Backup immutability

- **From:** Reliability R3 (Design for recovery)
- **Checklist item:** [RE:09](https://learn.microsoft.com/en-us/azure/well-architected/reliability/disaster-recovery) — Robust backup strategies (integrity of recovery data).
- **Phase:** 1 (decision)
- **Status:** Undecided

## What
- Decide whether WAL/basebackup blobs get an immutable (WORM) storage policy.
- If yes, set a retention window on the backup storage account/container.

## Why
- Protects backups from accidental or malicious deletion/tampering — the
  integrity half of a trustworthy recovery point.

## Guidance ([RE:09](https://learn.microsoft.com/en-us/azure/well-architected/reliability/disaster-recovery))
- Choose a backup approach per service and define **retention**.
- Store backups as **immutable (WORM)** so they can't be altered or deleted
  within the retention window; consider multi-region copies for recoverability.
- Protect and replicate all DR assets (backups, credentials, certs).
- Regularly test restores to confirm the backups are valid.
- Azure: enable a time-based **immutable blob** policy on the WAL/basebackup
  container.

## Done when
- Decision recorded (adopt WORM + window, or accept the risk with rationale).
