# AKS version-upgrade runbook

- **From:** Reliability R4 (Design for operations)
- **Checklist item:** [OE:02](https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/formalize-operations-tasks) — Standardize routine, ad-hoc, and emergency operations.
- **Phase:** 1
- **Status:** Likely gap in the RB catalog

## What
- Runbook for upgrading the AKS control plane and node pools.
- Cover: check supported versions, upgrade sequence, drain/surge settings,
  rollback, post-upgrade validation.

## Why
- AKS upgrades are a routine change that can break the cluster; a repeatable
  procedure keeps it a non-event.

## Guidance ([OE:02](https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/formalize-operations-tasks))
- Break the upgrade into a discrete, repeatable **checklist**: test in staging →
  raise a change record → upgrade control plane → upgrade node pools → validate
  → update docs.
- Reuse existing IaC + standard reliability/security tests during the upgrade.
- For emergency upgrades, mark which low-risk steps may be skipped with approval.
- Automate repetitive steps where practical.
- Store the runbook in **version control** with author + review dates; schedule
  periodic reviews.

## Done when
- Runbook added to the RB catalog and used for one real upgrade.
