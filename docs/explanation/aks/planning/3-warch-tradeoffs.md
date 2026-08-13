# 3. Well-Architected tradeoffs

Step 3 of the [WAF suggested learning process](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework#suggested-learning-process):
**recognize that improving one pillar usually costs another, and record which
tradeoffs this workload is consciously making.**

Each Microsoft tradeoffs article is written as *"pursuing pillar **X**, and the
bill that lands on pillar **Y**."* The sections below mirror that: one section
per pillar we pursue, listing every tradeoff Microsoft names, and recording how
DineSafeViz resolved it against the decisions in
[Step 1](1-warch-design-principles.md), [Step 2](2-warch-checklist.md), and
[`spec.md`](../../../ref/spec.md).

## Reading this document

| Column | Meaning |
|---|---|
| **Tradeoff** | Microsoft's exact heading for the tradeoff. |
| **Pillar impacted** | The pillar that *pays the cost* when we pursue this section's pillar. |
| **Decision** | How we resolved it — see below. |
| **Rationale** | The step-1/step-2/`spec.md` decision that drives it. |

**Decision** values:

- **Accepted** — we prioritized this section's pillar and knowingly took the hit
  on the impacted pillar. Qualifiers: *(min.)* small, *(capped/bounded)*
  deliberately limited.
- **Declined** — we resolved it the *other* way, prioritizing the impacted
  pillar instead.
- **N/A** — our architecture doesn't trigger this tradeoff.

## Headline

DineSafeViz is a **budget-first** workload (hard $100/mo cap, stop-by-default,
free/OSS preference). In WAF terms that means its consequential tradeoffs
cluster in **Cost Optimization** — we repeatedly chose the cheaper option and
*accepted* reduced resiliency, capacity, and observability. The mirror image is
that in the **Reliability**, **Security**, and **Performance** sections we
often **decline** the tradeoff, because we did not over-invest in those pillars
in the first place. One deliberate line is drawn: we do **not** trade away
security controls for cost — the cost-driven security omissions are premium
threat-monitoring extras (Defender, Firewall, Entra ID P1), risk-accepted and
backlogged, not core controls.

---

## Reliability tradeoffs

> Pursuing reliability. Source:
> https://learn.microsoft.com/en-us/azure/well-architected/reliability/tradeoffs

| Tradeoff | Pillar impacted | Decision | Rationale |
|---|---|---|---|
| Increased workload surface area | Security | **Accepted (min.)** | GRS + continuous WAL archive add a backup path to secure; capped — no message bus or extra runtime components (R5, RE:01) |
| Security control bypass | Security | **Declined** | Not designed in; incident-response runbooks keep controls on during triage |
| Old software versions | Security | **Declined** | Chose "get current, stay current" — AKS upgrade runbook + patching; we take the patch-churn reliability risk to avoid staleness |
| Increased implementation redundancy or waste | Cost | **Accepted (capped)** | multi-AZ + GRS only; **no** active-active, **no** reservations, single Postgres instance — the core cost/reliability line (C3, RE:05) |
| Increased investment in operations not aligned to requirements | Cost | **Declined** | No on-call rotation, no paid support contract, monitoring capped to Container Insights baseline (RE:10) |
| Increased operational complexity | Operational Excellence | **Accepted (min.)** | passive-cold DR + CloudNativePG add some complexity; capped by single region, no active-active (R3) |
| Increased effort to generate team knowledge and awareness | Operational Excellence | **Accepted (small)** | RB-01…16 runbook catalog to maintain; solo scale keeps it small (OE:02) |
| Increased latency | Performance | **N/A** | Async WAL, single region — no synchronous replication in the request path |
| Increased over-provisioning | Performance | **Declined** | We *under*-provision by design — stop-by-default, B2s burstable, autoscale from 1 — accepting scaling lag to save cost |

**Notable decisions**

- **Old software versions (Declined):** This is a genuine fork — Microsoft frames
  patching as a *reliability* risk (a patch can break a running component). We
  side with Security and patch anyway, mitigating the reliability side with the
  AKS upgrade runbook and stop-by-default (upgrades happen on a started cluster,
  observed, not on live traffic).
- **Redundancy vs waste (Accepted, capped):** We buy exactly two cheap forms of
  redundancy — multi-AZ node placement and geo-redundant backup storage — and
  stop there. Active-active, standing secondaries, and reserved capacity were
  evaluated and rejected on cost ([Step 1](1-warch-design-principles.md), C3).

---

## Security tradeoffs

> Pursuing security. Source:
> https://learn.microsoft.com/en-us/azure/well-architected/security/tradeoffs

| Tradeoff | Pillar impacted | Decision | Rationale |
|---|---|---|---|
| Increased complexity | Reliability | **Accepted (min.)** | default-deny Cilium NetworkPolicy, per-env isolation, per-pod RBAC add config surface; kept simple — baseline PSS in Phase 1 (SE:04, SE:08) |
| Increased critical dependencies | Reliability | **Accepted** | Entra ID (Workload Identity/OIDC), Key Vault, cert-manager/ACME are verify-explicitly SPOFs; accepted, degraded-state understood (SE:05, SE:09) |
| Increased complexity of disaster recovery | Reliability | **Accepted (min.)** | Key Vault access + encryption must be restored first in DR; folded into RB-16 (RE:09 backlog) |
| Increased rate of change | Reliability | **Accepted** | Patch cadence, 90-day ACME cert rotation, credential rotation cause transient failures; aligns with "get current" (SE:09) |
| Additional infrastructure | Cost | **Declined (mostly)** | Deliberately **no** SIEM/Defender, **no** Azure Firewall, **no** HSM; chose free/native controls — Key Vault, CSI, NetworkPolicy (SE:06, SE:10 deferred) |
| Increased demand on infrastructure | Cost | **Accepted (min.)** | Encryption at rest/host + TLS consume cycles; negligible on B2s; declined premium SKUs, log retention capped at 30 days (SE:07, CO:10) |
| Increased process and operational costs | Cost | **Accepted (bounded)** | Rotation runbooks, kube-bench, Dependabot/CodeQL cost time but are free OSS; no pen test, no paid tooling, no compliance audit (SE:01, SE:02) |
| Complications in observability and serviceability | Operational Excellence | **Accepted (min.)** | Segmentation complicates tracing; solo scale, small; no data-masking gap — app data is public |
| Decreased agility and increased complexity | Operational Excellence | **Accepted (bounded)** | GitHub Environments approval gate slows prod deploy by design; per-identity RBAC granularity (OE:11, SE:05) |
| Increased coordination efforts | Operational Excellence | **N/A** | Solo operator; no external compliance, org auditors, or breach-disclosure mandate |
| Increased latency and overhead | Performance | **Accepted (min.)** | TLS termination + identity verification + encryption; negligible at ~10 connections; no inline firewall/WAF |
| Increased chance of misconfiguration | Performance | **Accepted (managed)** | NetworkPolicy/RBAC rule risk; mitigated by IaC (Terraform/Helm) + kube-bench + least-privilege (SE:01) |

**Notable decisions**

- **Additional infrastructure (Declined):** The expensive security posture
  (Defender for Cloud, Azure Firewall, HSM, SIEM) is out on cost. The security
  *controls* we keep are the ones that are free at our scale — encryption,
  Workload Identity, Key Vault + CSI, default-deny NetworkPolicy, GitHub-native
  scanning. This keeps the "don't trade security for cost" line intact while
  respecting the budget.
- **Critical dependencies (Accepted):** Verify-explicitly means Entra ID and Key
  Vault become hard dependencies — if they're unavailable, verification fails and
  the workload degrades. We accept this rather than weaken auth; the DR runbook
  (RB-16) must restore these dependencies first.

---

## Cost Optimization tradeoffs

> Pursuing cost optimization — **the dominant pillar for this workload.** Source:
> https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/tradeoffs

| Tradeoff | Pillar impacted | Decision | Rationale |
|---|---|---|---|
| Reduced resiliency | Reliability | **Accepted** | stop-by-default, B2s burstable, single Postgres, hard $100 cap, budget SKUs, autoscale from 1 — accept a lower SLO; bounded by flow criticality + holding-page fallback (spec.md) |
| Limited recovery strategy | Reliability | **Accepted (bounded)** | passive-cold, 7-day PITR, ≤24h RPO, no paid support → slower recovery accepted within ≤4h RTO tier 2; drills backlogged (RE:08/09) |
| Increased complexity | Reliability | **Accepted (min.)** | stop-by-default automation, spot VMs, cheapest-region selection add ops complexity; capped — single region, one cluster (C3/C4) |
| Reduced security controls | Security | **Declined** | We did **not** cut security to save money — encryption, Workload Identity, Key Vault, default-deny, scanning all retained (all free); only premium threat-monitoring extras deferred, risk-accepted |
| Increased workload surface area | Security | **N/A** | No cost-optimizing components added (no CDN, message bus, Valet Key) — nothing new to secure |
| Removed segmentation | Security | **Accepted (bounded)** | One cluster hosts all workloads (CO:14); density raises blast radius; mitigated by per-env namespaces, NetworkPolicy, per-pod identities; prod/stg still separated |
| Compromised SDLC capacities | Operational Excellence | **Declined (partial)** | CI unit tests + linters kept as gates, IaC + docs + automation retained; only integration/e2e tests deferred to a later phase (OE:09) |
| Reduced observability | Operational Excellence | **Accepted (bounded)** | 30-day Log Analytics retention, baseline Container Insights only; full observability stack deferred to Phase 3 to save storage (OE:07, CO:10) |
| Deferred maintenance | Operational Excellence | **Declined** | Commit to patching (get current) + AKS upgrade runbook; no expiring vendor contracts (OSS) — maintenance not deferred for cost |
| Underprovisioned or underscaled resources | Performance | **Accepted** | B2s burstable, autoscale from 1, aggressive scale-down (stop-by-default) — accept spike vulnerability; justified by near-zero traffic + holding page (PE:01) |
| Lack of optimization over time | Performance | **Accepted (bounded)** | Phase 1 skips load testing + perf tooling (deferred Phase 2/3); accept undetected perf issues now; OE Level 1 → iterate (PE:04/06) |

**Notable decisions**

- **Reduced resiliency (Accepted) is the workload's defining tradeoff.** Almost
  every cost decision — stopping clusters, burstable SKUs, a single database
  instance, a hard spending cap — trades resiliency for money. It is defensible
  *only because* the criticality analysis says so: flows A/B fall back to a
  static holding page, flow C is best-effort, and there is no SLA to breach
  (spec.md). Change those assumptions and this row must be revisited first.
- **Reduced security controls (Declined) is the deliberate exception.** This is
  the one place we refuse the cost tradeoff — see the Security section above.

---

## Operational Excellence tradeoffs

> Pursuing operational excellence. Source:
> https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/tradeoffs

| Tradeoff | Pillar impacted | Decision | Rationale |
|---|---|---|---|
| Increased complexity | Reliability | **Accepted (min.)** | IaC (Terraform/Helm/Helmfile) + safe-deploy compatibility add surface; kept modular; single Postgres avoids blue/green data complexity (OE:05, OE:11) |
| Increased potentially destabilizing activities | Reliability | **Accepted (bounded)** | Frequent small GHA deploys raise change rate; mitigated by approval gate + digest promotion stg→prod + rolling updates; low frequency solo (OE:11) |
| Increased surface area | Security | **Accepted (min.)** | GHA runners + control-plane identities are in scope for hardening; kept minimal, least-privilege (SE:05) |
| Increased desire for transparency | Security | **N/A** | App data is public (Toronto Open Data) — no data-masking conflict with observability |
| Reduced segmentation | Security | **Accepted (bounded)** | Shared Log Analytics workspace eases querying but reduces row-level separation; acceptable — public data, per-env identities retained (CO:10) |
| Increased resource spending | Cost | **Accepted (capped)** | stg environment + safe-deploy concurrency add resources; capped by stop-by-default (idle ≈ 0) + staging parity decision; telemetry capped 30 days (CO:08) |
| Decreased focus on delivery activities | Cost | **N/A** | Solo, no on-call rotation; standardized runbook tasks bounded |
| Increased tooling demands and diversity | Cost | **Declined** | All tooling free OSS (tflint, hadolint, markdownlint, GHA, Dependabot, CodeQL) — no licensing, avoid sprawl (OE:04) |
| Increased resource utilization | Performance | **Accepted (min.)** | Container Insights + postgres_exporter instrumentation consume resources; minor on B2s (RE:10, OE:07) |
| Increased latency | Performance | **N/A** | No gateway routing / message broker / anti-corruption layer introduced — nginx ingress only |

**Notable decisions**

- **Tooling demands (Declined):** Operational maturity normally means buying
  tools. We reach the same standards with free OSS instead, so the OpEx-vs-Cost
  tradeoff Microsoft warns about largely doesn't land — a direct expression of
  the project's free-first cost policy.
- **Destabilizing activities (Accepted, bounded):** More frequent deploys is
  the OpEx-vs-Reliability tension. Our safe-deployment practices (approval gate,
  promote-by-digest, rolling updates) are exactly the mitigations Microsoft
  prescribes, and solo/low deploy frequency keeps the residual risk small.

---

## Performance Efficiency tradeoffs

> Pursuing performance efficiency — **deliberately loose for this workload.**
> Source:
> https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/tradeoffs

Performance targets are intentionally loose (PE:01, "loose by design"), so most
of these tradeoffs are **declined or N/A** — we are not chasing performance hard
enough to incur them.

| Tradeoff | Pillar impacted | Decision | Rationale |
|---|---|---|---|
| Reduced replication and increased density | Reliability | **Declined** | We don't pursue performance via density; the single-cluster density we do have is a *cost* decision (see Cost §) |
| Increased complexity | Reliability | **Declined** | No perf-driven autoscaling beyond basic cluster autoscaler, no sharding/partitioning, no denormalization, no cache — kept simple (P3/P4 deferred) |
| Testing and observation on active environments | Reliability | **N/A** | Perf/synthetic testing deferred to Phase 2 (k6); when adopted, runs against stg, not prod (PE:06) |
| Reduction of security controls | Security | **Declined** | We do **not** strip encryption/scanning/firewall rules for speed — performance never outranks security here |
| Increased workload surface area | Security | **N/A** | No perf components added (message bus, LB-for-autoscale, CDN, cache) |
| Removing segmentation | Security | **Accepted (bounded)** | Single-cluster density (shared with Cost §, CO:14) — not a perf-driven choice; mitigated by NetworkPolicy + per-pod identities |
| Stale security state | Security | **N/A** | No caching/CDN/edge/precomputed auth — direct SQL, fresh reads |
| Too much supply for demand | Cost | **N/A** | We under-provision, not over — no overprovisioning risk |
| More components | Cost | **Declined** | No extra perf components; consolidation favored (CO:14) |
| Increased investment on items not aligned to requirements | Cost | **Declined** | No premium SKUs, minimal perf telemetry, perf testing deferred, no perf-tuning services |
| Reduced observability | Operational Excellence | **Accepted (bounded)** | Baseline observability only in Phase 1 (same as Cost §) — full stack Phase 3 |
| Increased complexity in operations | Operational Excellence | **N/A** | No partitioning/sharding to complicate backups/rotation |
| Culture stress | Operational Excellence | **N/A** | Solo — blameless RCA trivial; off-peak ops scheduling flexible |

**Notable decisions**

- **Performance is where we *decline* the most.** Because targets are loose and
  traffic is near-zero, the classic performance tradeoffs (stripping controls
  for speed, adding caches/CDNs, over-tuning) simply never get made. The only
  performance-adjacent hit we take — single-cluster density — is booked as a
  **cost** decision, not a performance one.
