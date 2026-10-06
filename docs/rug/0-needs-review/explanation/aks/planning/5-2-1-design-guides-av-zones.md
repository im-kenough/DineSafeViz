# 5-2-1. Design guide — Availability zones and regions

> Source: [Architecture strategies for using availability zones and regions](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/regions-availability-zones)
>
> Parent: [5-2 Design guides](5-2-0-warch-design-guides.md) · Status: **records the single-region locality decision**

This guide helps decide **whether to spread a workload across availability zones, across regions, or neither** — a choice that trades reliability against cost, performance, and operational complexity. This document summarizes the guide's four deployment approaches, maps DineSafeViz's existing decisions onto them, and calls out gaps and any plan changes.

## Deployment options in the guide

The guide frames four approaches, from cheapest/least resilient to most:

| Approach | Reliability | Cost | Ops effort | One-line description |
| --- | --- | --- | --- | --- |
| **1. Locally redundant** | Low | Lowest | Low | Single region, no zone pinning; one instance. Optional variant: **+ backup across regions** (async) for DR. |
| **2. Zonal (pinned)** | Low alone / High multi-zone | Low → High | High | Resources pinned to a chosen zone. Real resiliency needs redundant instances in ≥2 zones + your own failover ("in-region / metro DR"). |
| **3. Zone-redundant** | High | Moderate | Low | Instances **and storage** spread across zones with **synchronous** replication; Microsoft handles failover. Variant: **+ backup across regions**. |
| **4. Multi-region** | High → Very high | High | High | Resources in ≥2 regions, active-passive or active-active, **async** (some data-loss risk) or **sync** (slow) replication. |

Key decision inputs the guide lists: **risk tolerance**, **reliability requirements (RTO/RPO/SLO)**, **data residency**, **user location**, **budget**, and **complexity**. Its default recommendation for *production* workloads is zone-redundant + backup across regions; it explicitly offers **locally redundant + backup across regions** as the low-cost option for internal, outage-tolerant apps.

## Which approach fits DineSafeViz

**Adopted: Approach 1 — locally redundant + backup across regions.** A single active region runs one instance of each component; PostgreSQL WAL + basebackups replicate **asynchronously** to **geo-redundant storage (GRS)**, giving a cross-region data copy without a standing secondary. This is the guide's exact *Internal application* recommendation, and it satisfies the decision inputs:

- **Risk tolerance / SLO** — no SLA; an AZ or region outage causing temporary unavailability is accepted, with a holding-page fallback ([Step 3](3-warch-tradeoffs.md)).
- **RTO/RPO** — RPO ≤ 24h and RTO ~20–30 min (tier 1) / ≤ 4h (tier 2) are met by backup frequency + IaC rebuild, exactly the guide's "recovery time = rebuild via IaC, recovery point = backup frequency" model.
- **Budget** — lowest-cost option; single instance, no inter-zone/region duplication of compute.
- **Data residency** — North America (latency-driven, no legal mandate), so residency doesn't force any particular approach.

Why the other approaches are **not** suitable:

| Approach | Suitable? | Reason |
| --- | --- | --- |
| **Zonal (pinned)** | No | Pinning to one zone adds no resiliency; realizing benefit needs redundant instances per zone + self-managed failover (extra cost). The colocation *performance* benefit is irrelevant — the workload isn't latency-sensitive (<1s budget met easily). |
| **Zone-redundant** | No | Requires ≥1 node per zone **and** a synchronous PostgreSQL standby set (CloudNativePG `instances: 3` spread across zones) — roughly multiplying DB compute/storage. Conflicts with the $100/mo cap, and the reliability target doesn't require it. This is the AZ tradeoff **declined** in [Step 3](3-warch-tradeoffs.md). |
| **Multi-region** | No | A standing secondary region is the mission-critical inverse of this workload — explicitly rejected (passive-cold, no standing DR cluster). The only cross-region element kept is **async backup** (GRS), which is the Approach-1 variant, not a multi-region deployment. |

## Mapping existing decisions to the guide

| Existing decision (source) | Guide concept |
| --- | --- |
| Single active region + cold DR region ([spec](../../../ref/spec.md#region--residency)) | Locally redundant **+ backup across regions** |
| Passive-cold, data-only DR ([spec](../../../ref/spec.md#recovery-targets)) | The async "backup across regions" layer |
| WAL + daily basebackup to **GRS** ([arch-design-aks]) | Asynchronous cross-region data replication (backup) |
| RPO ≤ 24h; RTO 20–30 min / ≤ 4h ([spec](../../../ref/spec.md#recovery-targets)) | Recovery point = backup frequency; recovery time = IaC rebuild |
| Provision DR from IaC at failover ([arch-design-aks]) | Guide's "rebuild in another region via IaC; rehearse the runbook" |
| No SLA; holding-page fallback ([Step 3](3-warch-tradeoffs.md)) | Risk tolerance: accepts temporary outage (Internal-app use case) |
| nginx ingress; no Front Door / Traffic Manager ([design-planning]) | Consistent with single-region — global load balancers are for multi-region/acceleration |
| Node pools zone-capable `[1,2,3]`, steady-state min = 1 ([arch-design-aks]) | **Latent** zone capability; at steady state (one node, one Postgres primary) the workload is **locally redundant**, not zone-redundant |

## Gaps

1. **Zone posture is described inconsistently.** The v1 arch docs specify zone-capable node pools (`[1,2,3]`, "distribute evenly", "activates on autoscale"), which reads as a zone-redundant intent, while the WAF planning docs treat availability zones as **declined**. The reality sits in between and is dominated by the data tier: with a **single** CloudNativePG primary (no standing synchronous standby), the workload is **locally redundant + backup across regions** regardless of how compute spreads. The docs should say so consistently.
2. **Primary region is unselected.** The [spec](../../../ref/spec.md#region--residency) defers the region to a cost check (v1 docs variously said East US 2 or Canada Central). The guide treats region choice as critical, and the backup approach adds a constraint (below).
3. **GRS depends on a paired region.** The cross-region backup relies on GRS replicating to Azure's *paired* region. This only works if the primary region **has a pair**. Both candidates (East US 2 → Central US; Canada Central → Canada East) are paired and support availability zones, so GRS works either way — but this must constrain the region choice (a newer, unpaired region would need GZRS or Storage object replication instead).

## Changes to the plan

- **Reconcile the zone language (documentation change, no infra change).** **"Locally redundant + backup across regions"** is the canonical description; the node pools stay zone-capable (specifying `zones [1,2,3]` costs nothing) but zone redundancy is **not realized** (single Postgres primary) and that is the accepted cost tradeoff. Zone-redundant compute/data is intentionally not pursued. Recorded in [spec.md](../../../ref/spec.md#region--residency).
- **Region selection is constrained to a paired, AZ-supporting NA region** so GRS replicates. The specific region stays **deferred to the cost check** (East US 2 and Canada Central both qualify); the paired + AZ constraint is now recorded in [spec.md](../../../ref/spec.md#region--residency).
- No change to the DR tier, RPO/RTO, or backup design — those already match the guide's Approach-1 variant.

[arch-design-aks]: ../../../0-needs-review/ref/arch/design-planning/arch-design-aks.md
[design-planning]: ../../../0-needs-review/ref/arch/design-planning/arch-design-planning.md
