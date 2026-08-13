# AKS version-upgrade runbook

- **From:** Reliability R4 (Design for operations)
- **Phase:** 1
- **Status:** Likely gap in the RB catalog

## What
- Runbook for upgrading the AKS control plane and node pools.
- Cover: check supported versions, upgrade sequence, drain/surge settings,
  rollback, post-upgrade validation.

## Why
- AKS upgrades are a routine change that can break the cluster; a repeatable
  procedure keeps it a non-event.

## Done when
- Runbook added to the RB catalog and used for one real upgrade.
