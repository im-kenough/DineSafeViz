# 3. Well-Architected tradeoffs

After deciding which checklist items to prioritize in [Step 2](2-warch-checklist.md), Step 3 of the [Well Architected Framework process](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework#suggested-learning-process) requires us to understand the trade offs given these decisions.

## Tradeoff analysis

DineSafeViz is a budget workload and favours the Cost Optimization pillar.
- As a result, we accepted reduced resiliency, capacity and observability.
- Core security controls were kept in place, and premium security features are risk accepted.

For each tradeoff within a pillar, we record a decision:

- **Accepted**: we pursue this pillar and take on the cost it imposes.
  - Raises the priority of this pillar.
  - Lowers the priority of the impacted pillar.
  - A qualifier notes *how much* of that cost we actually bear:
    - **(negligible)**: the cost is tiny at our scale.
    - **(capped)**: we set a hard limit so the cost can't grow.
    - **(mitigated)**: a specific mechanism offsets the risk.
    - **(no qualifier)**: the cost is fully accepted.
- **Rejected**: we hold back on this pillar to protect the impacted one
  - Lowers the priority of this pillar.
  - Raises the priority of the impacted pillar.
- **N/A**: our architecture doesn't trigger this tradeoff.

The **Pillar impacted** column names the pillar that is negatively impacted when we
pursue the section's pillar.

## Summary

| Pillar pursued | Accepted (fully) | Accepted (capped) | Accepted (mitigated) | Accepted (negligible) | Rejected | N/A | Total |
|---|---|---|---|---|---|---|---|
| Reliability | — | 3 | — | 1 | 4 | 1 | 9 |
| Security | 2 | 3 | 2 | 3 | 1 | 1 | 12 |
| Cost Optimization | 2 | 4 | 1 | — | 3 | 1 | 11 |
| Operational Excellence | — | 3 | 2 | 1 | 1 | 3 | 10 |
| Performance Efficiency | — | 1 | 1 | — | 5 | 6 | 13 |
| **Total** | **4** | **14** | **6** | **5** | **14** | **12** | **55** |

- 10 of 12 security tradeoffs were accepted to some degree, negatively impacting other pillars
- only 4 tradeoffs fully accepted and they are all in Security and Cost Optimization
  - if assumptions change these are the rows to review first.
- 5 of 13 performance tradeoffs were rejected. Deprioritized in favour of lowering costs.

## Reliability tradeoffs

> Pursuing reliability. Source:
> https://learn.microsoft.com/en-us/azure/well-architected/reliability/tradeoffs

Optimizing the Reliability pillar results in the trade offs below, at the detriment to elements in other pillars.

| Tradeoff | Decision | Pillar impacted | Rationale |
|---|---|---|---|
| Increased workload surface area | **Accepted (capped)** | Security | GRS + continuous WAL archive add a backup path to secure; capped: no message bus or extra runtime components (R5, RE:01) |
| Security control bypass | **Rejected** | Security | Not designed in; incident-response runbooks keep controls on during triage |
| Old software versions | **Rejected** | Security | Chose "get current, stay current": AKS upgrade runbook + patching; we take the patch-churn reliability risk to avoid staleness |
| Increased implementation redundancy or waste | **Accepted (capped)** | Cost | multi-AZ + GRS only; **no** active-active, **no** reservations, single Postgres instance: the core cost/reliability line (C3, RE:05) |
| Increased investment in operations not aligned to requirements | **Rejected** | Cost | No on-call rotation, no paid support contract, monitoring capped to Container Insights baseline (RE:10) |
| Increased operational complexity | **Accepted (capped)** | Operational Excellence | passive-cold DR + CloudNativePG add some complexity; capped by single region, no active-active (R3) |
| Increased effort to generate team knowledge and awareness | **Accepted (negligible)** | Operational Excellence | RB-01…16 runbook catalog to maintain; solo scale keeps it small (OE:02) |
| Increased latency | **N/A** | Performance | Async WAL, single region: no synchronous replication in the request path |
| Increased over-provisioning | **Rejected** | Performance | We *under*-provision by design: stop-by-default, B2s burstable, autoscale from 1: accepting scaling lag to save cost |

**Notable decisions**

- **Old software versions (Rejected):** This is a genuine fork: Microsoft frames
  patching as a *reliability* risk (a patch can break a running component). We
  side with Security and patch anyway, mitigating the reliability side with the
  AKS upgrade runbook and stop-by-default (upgrades happen on a started cluster,
  observed, not on live traffic).
- **Redundancy vs waste (Accepted, capped):** We buy exactly two cheap forms of
  redundancy: multi-AZ node placement and geo-redundant backup storage: and
  stop there. Active-active, standing secondaries, and reserved capacity were
  evaluated and rejected on cost ([Step 1](1-warch-design-principles.md), C3).

---

## Security tradeoffs

> Pursuing security. Source:
> https://learn.microsoft.com/en-us/azure/well-architected/security/tradeoffs

Optimizing the Security pillar results in the trade offs below, at the detriment to elements in other pillars.

| Tradeoff | Decision | Pillar impacted | Rationale |
|---|---|---|---|
| Increased complexity | **Accepted (capped)** | Reliability | default-deny Cilium NetworkPolicy, per-env isolation, per-pod RBAC add config surface; kept simple: baseline PSS in Phase 1 (SE:04, SE:08) |
| Increased critical dependencies | **Accepted** | Reliability | Entra ID (Workload Identity/OIDC), Key Vault, cert-manager/ACME are verify-explicitly SPOFs; accepted, degraded-state understood (SE:05, SE:09) |
| Increased complexity of disaster recovery | **Accepted (mitigated)** | Reliability | Key Vault access + encryption must be restored first in DR; folded into RB-16 (RE:09 backlog) |
| Increased rate of change | **Accepted** | Reliability | Patch cadence, 90-day ACME cert rotation, credential rotation cause transient failures; aligns with "get current" (SE:09) |
| Additional infrastructure | **Rejected** | Cost | Deliberately **no** SIEM/Defender, **no** Azure Firewall, **no** HSM; chose free/native controls: Key Vault, CSI, NetworkPolicy (SE:06, SE:10 deferred) |
| Increased demand on infrastructure | **Accepted (negligible)** | Cost | Encryption at rest/host + TLS consume cycles; negligible on B2s; declined premium SKUs, log retention capped at 30 days (SE:07, CO:10) |
| Increased process and operational costs | **Accepted (capped)** | Cost | Rotation runbooks, kube-bench, Dependabot/CodeQL cost time but are free OSS; no pen test, no paid tooling, no compliance audit (SE:01, SE:02) |
| Complications in observability and serviceability | **Accepted (negligible)** | Operational Excellence | Segmentation complicates tracing; solo scale, small; no data-masking gap: app data is public |
| Decreased agility and increased complexity | **Accepted (capped)** | Operational Excellence | GitHub Environments approval gate slows prod deploy by design; per-identity RBAC granularity (OE:11, SE:05) |
| Increased coordination efforts | **N/A** | Operational Excellence | Solo operator; no external compliance, org auditors, or breach-disclosure mandate |
| Increased latency and overhead | **Accepted (negligible)** | Performance | TLS termination + identity verification + encryption; negligible at ~10 connections; no inline firewall/WAF |
| Increased chance of misconfiguration | **Accepted (mitigated)** | Performance | NetworkPolicy/RBAC rule risk; mitigated by IaC (Terraform/Helm) + kube-bench + least-privilege (SE:01) |

**Notable decisions**

- **Additional infrastructure (Rejected):** The expensive security posture
  (Defender for Cloud, Azure Firewall, HSM, SIEM) is out on cost. The security
  *controls* we keep are the ones that are free at our scale: encryption,
  Workload Identity, Key Vault + CSI, default-deny NetworkPolicy, GitHub-native
  scanning. This keeps the "don't trade security for cost" line intact while
  respecting the budget.
- **Critical dependencies (Accepted):** Verify-explicitly means Entra ID and Key
  Vault become hard dependencies: if they're unavailable, verification fails and
  the workload degrades. We accept this rather than weaken auth; the DR runbook
  (RB-16) must restore these dependencies first.

---

## Cost Optimization tradeoffs

> Pursuing cost optimization: **the dominant pillar for this workload.** Source:
> https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/tradeoffs

Optimizing the Cost Optimization pillar results in the trade offs below, at the detriment to elements in other pillars.

| Tradeoff | Decision | Pillar impacted | Rationale |
|---|---|---|---|
| Reduced resiliency | **Accepted** | Reliability | stop-by-default, B2s burstable, single Postgres, hard $100 cap, budget SKUs, autoscale from 1: accept a lower SLO; bounded by flow criticality + holding-page fallback (spec.md) |
| Limited recovery strategy | **Accepted (capped)** | Reliability | passive-cold, 7-day PITR, ≤24h RPO, no paid support → slower recovery accepted within ≤4h RTO tier 2; drills backlogged (RE:08/09) |
| Increased complexity | **Accepted (capped)** | Reliability | stop-by-default automation, spot VMs, cheapest-region selection add ops complexity; capped: single region, one cluster (C3/C4) |
| Reduced security controls | **Rejected** | Security | We did **not** cut security to save money: encryption, Workload Identity, Key Vault, default-deny, scanning all retained (all free); only premium threat-monitoring extras deferred, risk-accepted |
| Increased workload surface area | **N/A** | Security | No cost-optimizing components added (no CDN, message bus, Valet Key): nothing new to secure |
| Removed segmentation | **Accepted (mitigated)** | Security | One cluster hosts all workloads (CO:14); density raises blast radius; mitigated by per-env namespaces, NetworkPolicy, per-pod identities; prod/stg still separated |
| Compromised SDLC capacities | **Rejected** | Operational Excellence | CI unit tests + linters kept as gates, IaC + docs + automation retained; only integration/e2e tests deferred to a later phase (OE:09) |
| Reduced observability | **Accepted (capped)** | Operational Excellence | 30-day Log Analytics retention, baseline Container Insights only; full observability stack deferred to Phase 3 to save storage (OE:07, CO:10) |
| Deferred maintenance | **Rejected** | Operational Excellence | Commit to patching (get current) + AKS upgrade runbook; no expiring vendor contracts (OSS): maintenance not deferred for cost |
| Underprovisioned or underscaled resources | **Accepted** | Performance | B2s burstable, autoscale from 1, aggressive scale-down (stop-by-default): accept spike vulnerability; justified by near-zero traffic + holding page (PE:01) |
| Lack of optimization over time | **Accepted (capped)** | Performance | Phase 1 skips load testing + perf tooling (deferred Phase 2/3); accept undetected perf issues now; OE Level 1 → iterate (PE:04/06) |

**Notable decisions**

- **Reduced resiliency (Accepted) is the workload's defining tradeoff.** Almost
  every cost decision: stopping clusters, burstable SKUs, a single database
  instance, a hard spending cap: trades resiliency for money. It is defensible
  *only because* the criticality analysis says so: flows A/B fall back to a
  static holding page, flow C is best-effort, and there is no SLA to breach
  (spec.md). Change those assumptions and this row must be revisited first.
- **Reduced security controls (Rejected) is the deliberate exception.** This is
  the one place we refuse the cost tradeoff: see the Security section above.

---

## Operational Excellence tradeoffs

> Pursuing operational excellence. Source:
> https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/tradeoffs

Optimizing the Operational Excellence pillar results in the trade offs below, at the detriment to elements in other pillars.

| Tradeoff | Decision | Pillar impacted | Rationale |
|---|---|---|---|
| Increased complexity | **Accepted (capped)** | Reliability | IaC (Terraform/Helm/Helmfile) + safe-deploy compatibility add surface; kept modular; single Postgres avoids blue/green data complexity (OE:05, OE:11) |
| Increased potentially destabilizing activities | **Accepted (mitigated)** | Reliability | Frequent small GHA deploys raise change rate; mitigated by approval gate + digest promotion stg→prod + rolling updates; low frequency solo (OE:11) |
| Increased surface area | **Accepted (capped)** | Security | GHA runners + control-plane identities are in scope for hardening; kept minimal, least-privilege (SE:05) |
| Increased desire for transparency | **N/A** | Security | App data is public (Toronto Open Data): no data-masking conflict with observability |
| Reduced segmentation | **Accepted (mitigated)** | Security | Shared Log Analytics workspace eases querying but reduces row-level separation; acceptable: public data, per-env identities retained (CO:10) |
| Increased resource spending | **Accepted (capped)** | Cost | stg environment + safe-deploy concurrency add resources; capped by stop-by-default (idle ≈ 0) + staging parity decision; telemetry capped 30 days (CO:08) |
| Decreased focus on delivery activities | **N/A** | Cost | Solo, no on-call rotation; standardized runbook tasks bounded |
| Increased tooling demands and diversity | **Rejected** | Cost | All tooling free OSS (tflint, hadolint, markdownlint, GHA, Dependabot, CodeQL): no licensing, avoid sprawl (OE:04) |
| Increased resource utilization | **Accepted (negligible)** | Performance | Container Insights + postgres_exporter instrumentation consume resources; minor on B2s (RE:10, OE:07) |
| Increased latency | **N/A** | Performance | No gateway routing / message broker / anti-corruption layer introduced: nginx ingress only |

**Notable decisions**

- **Tooling demands (Rejected):** Operational maturity normally means buying
  tools. We reach the same standards with free OSS instead, so the OpEx-vs-Cost
  tradeoff Microsoft warns about largely doesn't land: a direct expression of
  the project's free-first cost policy.
- **Destabilizing activities (Accepted, mitigated):** More frequent deploys is
  the OpEx-vs-Reliability tension. Our safe-deployment practices (approval gate,
  promote-by-digest, rolling updates) are exactly the mitigations Microsoft
  prescribes, and solo/low deploy frequency keeps the residual risk small.

---

## Performance Efficiency tradeoffs

> Pursuing performance efficiency: **deliberately loose for this workload.**
> Source:
> https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/tradeoffs

Optimizing the Performance Efficiency pillar results in the trade offs below, at the detriment to elements in other pillars.

Performance targets are intentionally loose (PE:01, "loose by design"), so most
of these tradeoffs are **rejected or N/A**: we are not chasing performance hard
enough to incur them.

| Tradeoff | Decision | Pillar impacted | Rationale |
|---|---|---|---|
| Reduced replication and increased density | **Rejected** | Reliability | We don't pursue performance via density; the single-cluster density we do have is a *cost* decision (see Cost §) |
| Increased complexity | **Rejected** | Reliability | No perf-driven autoscaling beyond basic cluster autoscaler, no sharding/partitioning, no denormalization, no cache: kept simple (P3/P4 deferred) |
| Testing and observation on active environments | **N/A** | Reliability | Perf/synthetic testing deferred to Phase 2 (k6); when adopted, runs against stg, not prod (PE:06) |
| Reduction of security controls | **Rejected** | Security | We do **not** strip encryption/scanning/firewall rules for speed: performance never outranks security here |
| Increased workload surface area | **N/A** | Security | No perf components added (message bus, LB-for-autoscale, CDN, cache) |
| Removing segmentation | **Accepted (mitigated)** | Security | Single-cluster density (shared with Cost §, CO:14): not a perf-driven choice; mitigated by NetworkPolicy + per-pod identities |
| Stale security state | **N/A** | Security | No caching/CDN/edge/precomputed auth: direct SQL, fresh reads |
| Too much supply for demand | **N/A** | Cost | We under-provision, not over: no overprovisioning risk |
| More components | **Rejected** | Cost | No extra perf components; consolidation favored (CO:14) |
| Increased investment on items not aligned to requirements | **Rejected** | Cost | No premium SKUs, minimal perf telemetry, perf testing deferred, no perf-tuning services |
| Reduced observability | **Accepted (capped)** | Operational Excellence | Baseline observability only in Phase 1 (same as Cost §): full stack Phase 3 |
| Increased complexity in operations | **N/A** | Operational Excellence | No partitioning/sharding to complicate backups/rotation |
| Culture stress | **N/A** | Operational Excellence | Solo: blameless RCA trivial; off-peak ops scheduling flexible |

**Notable decisions**

- **Performance is where we *reject* the most.** Because targets are loose and
  traffic is near-zero, the classic performance tradeoffs (stripping controls
  for speed, adding caches/CDNs, over-tuning) simply never get made. The only
  performance-adjacent hit we take: single-cluster density: is booked as a
  **cost** decision, not a performance one.
