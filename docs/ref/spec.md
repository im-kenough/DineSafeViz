# DineSafeViz — Design Decision Register (spec)

Canonical record of workload-level design decisions: the numbers and
non-negotiables that other planning documents reference instead of restating.
When a value is decided here, cite it from the WAF planning docs rather than
duplicating it.

> Status: living document. Populated as the WAF planning process
> (`docs/explanation/aks/planning/`) resolves each decision.

## Business & availability targets

| Decision | Value | Notes / source |
|---|---|---|
| Workload purpose | Personal portfolio demo (Toronto DineSafe data viz) | Not a revenue/SLA-bound service |
| Availability model | On-demand; **clusters stopped by default**, started for demos | No 24/7 uptime |
| Formal SLA | **None** | AKS Free control plane has no uptime SLA |
| Expected load | Near-zero real traffic; shown to employers on demand | No user-growth forecast |
| Concurrent connections target | _TBD_ | To size Postgres `max_connections`, Flask workers |
| Dataset scale | ~100k rows, grows slowly | Toronto Open Data DineSafe feed |

## Critical user flows

| Flow | Description | Criticality | Accepted degraded state |
|---|---|---|---|
| A | Visitor browses inspection data (Flask pages) | **Critical** | Holding page via manual DNS flip |
| B | Visitor views embedded Grafana dashboard | **Critical** | Holding page via manual DNS flip |
| C | Nightly ETL refresh from Toronto Open Data | **Best-effort** | A missed refresh is acceptable |

## Recovery targets

| Decision | Value | Scenario |
|---|---|---|
| RPO | **≤ 24h** | Continuous WAL archive + daily basebackup to geo-redundant storage |
| RTO (tier 1) | **~20–30 min** | Pod/node self-healing within a running cluster (CloudNativePG) |
| RTO (tier 2) | **≤ 4h** | Full passive-cold regional DR: provision from IaC, restore WAL, repoint DNS |
| DR strategy | Passive-cold (backup-and-restore), data-only | No standing secondary cluster |

## Region & residency

| Decision | Value | Notes |
|---|---|---|
| Region scope | Single active region + cold DR region | |
| Residency constraint | **North America** (latency-driven) | No legal residency requirement |
| Specific region | _TBD at implementation — cheapest NA option_ | v1 docs variously said East US 2 / Canada Central; deferred to cost check |

## Cost / FinOps

| Decision | Value | Notes |
|---|---|---|
| Hard budget cap | **$100 USD/month** | Shut everything down at 100% |
| Budget alerts | **50%, 80%** of cap | Warnings |
| Steady-state target | **$25–50 USD/month** | Clusters stopped by default |

## Maturity target

| Decision | Value | Notes |
|---|---|---|
| WAF maturity level | **Operational Excellence Level 1**, iterate | Establish a solid foundation first |
