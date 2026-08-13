# DineSafeViz — Design Decision Register (spec)

## Business & availability targets

| Decision | Value | Notes / source |
|---|---|---|
| Workload purpose | Personal portfolio demo (Toronto DineSafe data viz) | Not a revenue/SLA-bound service |
| Availability model | On-demand; **clusters stopped by default**, started for demos | No 24/7 uptime |
| Formal SLA | **None** | AKS Free control plane has no uptime SLA |
| Expected load | Near-zero real traffic; shown to employers on demand | No user-growth forecast |
| Concurrent connections target | **~10** | Sizes Postgres `max_connections`, Flask workers (PE:01) |
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

## Performance targets

| Decision | Value | Notes / source |
|---|---|---|
| Query budget (flows A/B) | **< 1s** | Sub-second page/dashboard queries (PE:01) |
| Concurrent connections | **~10** | See Business & availability above |

## Data retention

| Decision | Value | Notes / source |
|---|---|---|
| Log Analytics | **30 days** | Container Insights logs in `log-dsv-shared-eus2` (CO:10) |
| Postgres PITR window | **7 days** | Daily basebackup + continuous WAL; covers the ≤24h RPO (CO:10) |
| ACR images | **Untagged-image cleanup** | Scheduled cleanup workflow removes untagged images (CO:07/CO:10) |

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
