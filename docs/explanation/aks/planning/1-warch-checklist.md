# 1. Well-Architected Checklists

Step 2 of the [WAF suggested learning process](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework#suggested-learning-process):
**prioritize the checklist items relevant to this workload; defer the rest.**

Each item inherits the stance set in [0-warch-design-principles.md](0-warch-design-principles.md).
Priority legend (phase in which the item is prioritized):

- **P1** — Phase 1 (now). Items partly done now sit here; the deferred slice is noted.
- **P2** — Phase 2.
- **P3** — Phase 3.
- **N/A** — not applicable (reason noted).

Open items link to [backlog](../../backlog/README.md); canonical targets live in
[spec.md](../../../ref/spec.md).

## Reliability

Source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/checklist

| Code | Recommendation | Priority | Maps to / note |
|---|---|---|---|
| RE:01 | Simplicity & efficiency | P1 | R5 |
| RE:02 | Identify & rate flows | P1 | R1 — A/B critical, C best-effort (spec.md) |
| RE:03 | Failure mode analysis | P1 | R2 — [FMA](../../backlog/failure-mode-analysis.md) |
| RE:04 | Reliability & recovery targets | P1 | R1/R3 — RPO/RTO in spec.md |
| RE:05 | Redundancy for critical flows | P1 | R2 — multi-AZ + GRS now; data-tier HA → P2 |
| RE:06 | Scaling strategy | P1 | R2 — cluster autoscaler now; HPA → P2 |
| RE:07 | Self-preservation / self-healing | P1 | R2/R3 — probes, CloudNativePG |
| RE:08 | Resiliency (chaos) testing | P3 | R4 — [failure simulation](../../backlog/failure-simulation.md) |
| RE:09 | DR plans (structured, tested) | P1 | R3 — pattern now; [RB-16](../../backlog/dr-runbook-rb16.md) + [drill](../../backlog/recovery-drill.md) → P2 |
| RE:10 | Health monitoring & indicators | P1 | R4 — Container Insights now; full stack → P3 |

## Security

Source: https://learn.microsoft.com/en-us/azure/well-architected/security/checklist

| Code | Recommendation | Priority | Maps to / note |
|---|---|---|---|
| SE:01 | Security baseline | P1 | S1/S5 — platform defaults now; secure-score/posture → P2 |
| SE:02 | Secure development lifecycle | P1 | S3 — light SDL now; image scanning → P2 |
| SE:03 | Data classification | P1 | S2 — app data public; secrets sensitive |
| SE:04 | Segmentation & perimeters | P1 | S1 — per-env isolation, NetworkPolicy |
| SE:05 | Identity & access management | P1 | S2/S3 — Workload Identity, RBAC, OIDC |
| SE:06 | Network traffic isolation | P1 | S2 — default-deny now; egress filtering (Firewall) → P2 |
| SE:07 | Encryption | P1 | S2 — at rest + at host + TLS |
| SE:08 | Harden resources | P1 | S3/S4 — hardening now; PSS-restricted → P2 |
| SE:09 | Protect secrets + rotation | P1 | S1/S2 — Key Vault + CSI, rotation workflow |
| SE:10 | Threat monitoring / detection | P2 | S5 — no SIEM/Defender in P1 |
| SE:11 | Security testing regimen | P2 | S5 — [image vuln scanning](../../backlog/image-vulnerability-scanning.md); no pen test |
| SE:12 | Incident response procedures | P2 | S1 — [security IR plan](../../backlog/security-incident-response.md) |

## Cost Optimization

Source: https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/checklist

| Code | Recommendation | Priority | Maps to / note |
|---|---|---|---|
| CO:01 | Culture of financial responsibility | P1 | C1 |
| CO:02 | Cost model | P1 | C1 |
| CO:03 | Collect & review cost data | P1 | C5 — alerts now; [review cadence](../../backlog/cost-alert-review-cadence.md) |
| CO:04 | Spending guardrails | P1 | C2 — budget alerts + auto-shutdown |
| CO:05 | Best rates from providers | P1 | C4 — spot, cheapest NA region, no reservations |
| CO:06 | Align usage to billing increments | P1 | C3/C4 — burstable + stop-by-default |
| CO:07 | Optimize component costs | P1 | C5 — remove unused; ACR cleanup |
| CO:08 | Optimize environment costs | P1 | C2 — prod/stg stopped by default |
| CO:09 | Optimize flow costs | P1 | C4 |
| CO:10 | Optimize data costs | P1 | storage — Standard HDD, LRS/GRS split, retention |
| CO:11 | Optimize code costs | P1 | single ETL CronJob; direct SQL |
| CO:12 | Optimize scaling costs | P1 | C3 — autoscaler + spot |
| CO:13 | Optimize personnel time | P1 | O4 — automation reduces toil |
| CO:14 | Consolidate resources | P1 | C4 — one cluster hosts all workloads |

## Operational Excellence

Source: https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/checklist

| Code | Recommendation | Priority | Maps to / note |
|---|---|---|---|
| OE:01 | Standard practices / DevOps culture | P1 | O1 — solo scale |
| OE:02 | Standardize operations (routine/emergency) | P1 | O1/O5 — runbook catalog; [AKS upgrade runbook](../../backlog/aks-upgrade-runbook.md) |
| OE:03 | Formalize development practices | P1 | O2 — lightweight, solo |
| OE:04 | Tools, QA, source control, style | P1 | O2 |
| OE:05 | Infrastructure as Code | P1 | O5 — Terraform + Helm/Helmfile |
| OE:06 | Workload supply chain / pipelines | P1 | O5 — GHA now; e2e tests → P2 |
| OE:07 | Monitoring stack | P1 | O3 — baseline now; full stack → P3 |
| OE:08 | Incident management | P2 | O1/S1 — [incident-review](../../backlog/incident-review-process.md) |
| OE:09 | Testing | P2 | O2 — synthetic e2e |
| OE:10 | Automation (reliable, secure) | P1 | O4 — core strength |
| OE:11 | Safe deployment practices | P1 | O5 — pipelines + approval gate; progressive rollout minimal |

## Performance Efficiency

Source: https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/checklist

| Code | Recommendation | Priority | Maps to / note |
|---|---|---|---|
| PE:01 | Define performance targets | P2 | P1 — loose by design; connection target TBD (spec.md) |
| PE:02 | Capacity planning | P2 | P2 — vertical scaling if needed |
| PE:03 | Select the right services | P1 | P2 — AKS/Postgres/SSD chosen (tech-choices) |
| PE:04 | Consistent performance measurement | P3 | P3 — baseline metrics only in P1 |
| PE:05 | Optimize scaling & partitioning | P2 | P2 — autoscaler now; HPA → P2 |
| PE:06 | Performance testing | P2 | P3 — k6 load test |
| PE:07 | Optimize code & infrastructure | P1 | P3 — offload to platform; right-sized |
| PE:08 | Optimize data usage | P1 | P2 — indexes on filtered columns |
| PE:09 | Prioritize critical-flow performance | P1 | P1 — flows A/B identified |
| PE:10 | Optimize operational tasks | P1 | backups, rotation, deploy impact |
| PE:11 | Respond to live performance issues | P3 | P3 |
| PE:12 | Continuously optimize | P3 | P4 |
