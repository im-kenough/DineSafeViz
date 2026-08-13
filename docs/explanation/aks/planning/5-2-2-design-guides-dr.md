# 5-2-2. Design guide — Disaster recovery

> Source: [Develop a disaster recovery (DR) plan for multi-region deployments](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/disaster-recovery)
>
> Parent: [5-2 Design guides](5-2-0-warch-design-guides.md) · Status: **records the DR strategy; runbook is backlog**

This guide turns a DR *strategy* into an executable *plan*: classify each workload by business criticality, pick a recovery posture that matches, then document a runbook, communication plan, and escalation path — and test them. This document summarizes those choices, maps DineSafeViz's existing DR decisions onto them, and calls out gaps.

## What the guide covers

**1. Criticality tiers** — right-size recovery to business impact:

| Tier | Typical SLO | RTO / RPO | Deployment posture |
| --- | --- | --- | --- |
| **0 Mission Critical** | > 99.99% | RTO seconds, RPO ~0 | Active-active, multi-region |
| **1 Business Critical** | ~99.95% | Minutes | Active-active or warm standby |
| **2 Business Operational** | ~99.9% | Hours | Active-passive warm/cold standby |
| **3 Administrative** | < 99.9% | RTO hours–days, RPO hours | Backup and restore |

**2. Recovery strategies** (each builds on the one below): active-active → warm standby → **cold standby** → **backup-and-restore**. The guide states backup-and-restore *"must be part of all recovery strategies."*

**3. The DR plan** = a version-controlled **runbook** (step-by-step failover *and* failback), a **communication plan**, and an **escalation path** with severity levels.

**4. Friction points** to avoid: expectations-vs-budget mismatch, shared/third-party dependencies, unclear activation criteria, and neglected failback.

**5. Test regularly** — rehearse the runbook and run restore/failover drills; an untested plan is unproven.

## Which strategy fits DineSafeViz

**Criticality: Tier 2 (Business Operational).** The workload is a no-SLA portfolio demo with clusters stopped by default; flows A/B are "critical" to a live demo but tolerate the holding-page fallback. RTO ≤ 4h and RPO ≤ 24h sit in the Tier-2 "hours" band. Within Tier 2 the guide permits either warm or cold standby — DineSafeViz deliberately takes the **cheapest posture the tier allows** (cold standby on a backup-and-restore foundation).

**Adopted: backup-and-restore + active-passive cold standby.** The primary region serves all traffic; the secondary region runs **nothing** until a disaster. CloudNativePG streams WAL + daily basebackups to **GRS** Blob; at failover a new cluster is provisioned from IaC and bootstrapped from that backup (CloudNativePG `bootstrap.recovery` → `externalClusters`, with point-in-time recovery). This is exactly the guide's cold-standby pattern and its "backup-and-restore must underpin every tier" rule.

Why the other postures are **not** suitable:

| Posture | Suitable? | Reason |
| --- | --- | --- |
| **Active-active** (Tier 0/1) | No | The mission-critical inverse — two regions serving live traffic. No revenue/SLA justifies the cost; rejected under the $100/mo cap. |
| **Warm standby** (Tier 1/2) | No | Keeps minimal compute running in the secondary 24/7. With near-zero traffic and stop-by-default clusters, paying for *any* standing secondary isn't defensible. Cold standby chosen instead. |
| **Backup-and-restore alone** | Partially | It's the foundation and is fully adopted — but paired with cold-standby readiness (IaC-provisioned secondary, DNS cutover) so recovery is repeatable, not ad hoc. |

## Mapping existing decisions to the guide

| Existing decision (source) | Guide concept |
| --- | --- |
| Passive-cold, data-only DR ([spec](../../../ref/spec.md#recovery-targets)) | **Active-passive cold standby** |
| Backup-and-restore is the coldest tier ([arch-design-aks]) | The **backup-and-restore** foundation (required for all tiers) |
| WAL + daily basebackup to **GRS** Blob ([arch-design-aks]) | Cold-standby "geo-redundant backup, stored in the secondary region" |
| RPO ≤ 24h ([spec](../../../ref/spec.md#recovery-targets)) | Backup frequency (continuous WAL + daily basebackup) |
| RTO ≤ 4h — manual cluster start + promotion ([arch-design-aks]) | Recovery time = provision + restore + cutover |
| Identical Terraform module, DR as a parallel instantiation ([arch-design-aks]) | "Deploy IaC with compute stopped; automate provisioning only when needed" |
| Failover updates an Azure DNS A record ([arch-design-aks]) | Traffic cutover step ("update DNS records if necessary") — the frugal substitute for Front Door/Traffic Manager, which are rejected on cost |
| CloudNativePG restore from Barman object store | Cold-standby step 7: "restore data from backups, validate RPO" |
| Teardown/route-back workflow ([arch-design-aks]) | **Failback** (considered, not yet detailed) |
| No standing secondary; Front Door/active-active deferred ([arch-design-aks]) | Cold standby (secondary stopped) |

## Gaps

1. **DR runbook (RB-16) is unwritten.** It's named in the spec but not authored ([arch-design-aks]). The guide treats the runbook as essential and says to *"treat it like production code — version it and make it reachable during an outage."* This is the biggest gap.
2. **DR activation criteria aren't documented.** The guide stresses activation criteria *"must be crystal clear."* For DineSafeViz these are proposable now: declare DR on a **primary-region outage**, **loss of control-plane/API access**, or **production data corruption** that in-cluster self-healing (tier-1 RTO) can't resolve.
3. **No restore/failover drill cadence.** The guide requires regular testing; none is scheduled. A lightweight fit: a **quarterly restore drill** to the staging environment, timing it against the ≤4h RTO.
4. **Failback is undetailed.** A teardown/route-back workflow exists but there's no documented, tested failback procedure — the guide warns failback is as important as failover.
5. **DR secondary must be the primary's Azure pair.** The v1 docs hand-named West US 2 as the DR region for an East US 2 primary, but GRS replicates to a region's *defined pair*. Since the region is deferred ([5-2-1](5-2-1-design-guides-av-zones.md)), the secondary should simply follow the chosen primary's pairing — not a hand-picked region.

**Not applicable:** the guide's full communication and executive-escalation plans assume an organization with stakeholders, on-call tiers, and C-level sign-off. DineSafeViz is a single-operator portfolio project, so those collapse to "the operator decides and acts." Only the *activation criteria* (gap 2) carry over.

## Changes to the plan

- **No change to the DR strategy.** Backup-and-restore + active-passive cold standby is the correct, guide-aligned choice for this criticality tier. RPO/RTO, GRS backup, and IaC-provisioned recovery already match.
- **Backlog — author RB-16**, covering: the CloudNativePG `bootstrap.recovery` restore step (from GRS Blob), the Azure DNS cutover, health validation, and the **failback/teardown** procedure. Version it in the repo.
- **Backlog — document activation criteria and a restore-drill cadence** (proposed criteria and quarterly drill above).
- **Consistency** — ensure the DR secondary region is whatever the chosen primary's Azure pair is ([5-2-1](5-2-1-design-guides-av-zones.md)), replacing the v1 hand-named West US 2.

[arch-design-aks]: ../../../0-needs-review/ref/arch/design-planning/arch-design-aks.md
