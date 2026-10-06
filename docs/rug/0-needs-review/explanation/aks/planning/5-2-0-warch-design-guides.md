# 5-2. Select Azure services — design guides

Step 5 of the [Well-Architected Framework process](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework#suggested-learning-process) also draws on the [design guides](https://learn.microsoft.com/en-us/azure/well-architected/design) (formerly "design essentials"). A design guide is *horizontal*: it takes a single cross-cutting practice or decision point and shows how it plays out across services and pillars. Where the [service guides](5-1-warch-service-guides.md) answer "how do I configure *this service*," the design guides answer "how do I handle *this concern*."

Design guides are **strategy and decision-point guidance, not reference architectures** — they describe how to think about a concern, not a deployable blueprint to copy. (Reference architectures are a separate Microsoft artifact in the Azure Architecture Center, such as the [AKS baseline architecture](https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/containers/aks/baseline-aks).) So "relevant" doesn't mean "build now": most of these guides describe decisions DineSafeViz has *already made*, and only a couple represent open work.

## Summary

Seven of the nine catalog guides apply to DineSafeViz, but they split by **status** rather than importance. Only one is active work to take on now, one is tracked open work, four are already reflected in the architecture, and one is backlogged. Two guides don't apply at all.

| Design guide | Status |
| --- | --- |
| [Availability zones & regions](#regions-availability-zones) | **Adopt now** — record the single-region decision |
| [Health modeling](#health-modeling) | **Backlog (open work)** — answers open RE:04 / RE:10 |
| [Optimize workload using flows](#flows) | Already applied |
| [Disaster recovery plan](#disaster-recovery-plan) | Already applied |
| [Background jobs](#background-jobs) | Already applied |
| [Continuous integration](#continuous-integration) | Already applied |
| [Handling transient faults](#handling-transient-faults) | Backlog |
| Data partitioning | Not applicable |
| Well-Architected Review assessment | Not applicable |

## Adopt now

### Architecture strategies for using availability zones and regions {#regions-availability-zones}

> Source: [Architecture strategies for using availability zones and regions](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/regions-availability-zones)

- **What the guide covers:** the reliability-vs-cost tradeoff of deploying across zones and/or regions, and how to choose a locality model that matches reliability objectives.
- **How it applies to DineSafeViz:** It's the guide that **justifies the single-region, single-zone decision**. The workload knowingly forgoes zonal and regional redundancy to stay under the $100/mo cap, and accepts the resulting availability ceiling (documented as a Reliability tradeoff in [Step 3](3-warch-tradeoffs.md)). The one exception — geo-redundant **GRS** backup storage — is exactly the "protect the data even if you don't replicate the compute" pattern this guide endorses.
- **Why "adopt now":** the decision is already made but not yet written down against this guide; recording the locality choice and its rationale is cheap and anchors the whole reliability narrative.

## Tracked open work

### Health modeling {#health-modeling}

> Source: [Health modeling for workloads](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/health-modeling)

This guide is the one genuine piece of pending design work in Step 5. It answers the questions [Step 2](2-warch-checklist.md) flagged but left open — **RE:04** (define a health model) and **RE:10** (measure with SLIs) — so it's backlogged as tracked open work rather than buried with the rest. The full model is documented in **[5-2-3](5-2-3-design-guides-health-modelling.md)**.

- **What the guide covers:** combining raw telemetry with business context to classify each entity as **Healthy / Degraded / Unhealthy**, deriving those states from **health signals** (metrics, logs, probes, SLIs/SLOs), and modeling entities-and-relationships so an alert fires on *flow* health rather than on every underlying resource. It's a **logical design exercise, tool-agnostic** — you define what "healthy" means, then wire it into whatever monitoring stack you run.
- **How it applies to DineSafeViz:**
  - The **flow model already exists** — flows A/B critical, flow C (ETL) best-effort — which is exactly the "contextualize by business impact" input the guide asks for. The health model is built directly on those flows, plus the shared PostgreSQL entity.
  - **SLIs map to existing budgets:** the <1s query budget and the tier-1 ~20–30min / tier-2 ≤4h RTOs become the thresholds that separate Healthy from Degraded from Unhealthy.
  - **Signals partly exist today:** the app's `/readyz` probe and CloudNativePG `status.conditions` are usable now; there is **no metrics/alerting pipeline yet**, so the measurement backend is an open tooling decision (not the Prometheus stack assumed earlier). The managed *Azure Monitor health models* feature is declined as a paid layer, keeping to the free/OSS-first preference.
  - **Retention aligns for free** — the guide recommends not keeping health data beyond **30 days**, matching the retention already set for cost ([5-1](5-1-warch-service-guides.md#log-analytics)).
- **The open work:** define per-flow health states, choose the tooling to compute SLIs, and alert on rolled-up flow health instead of raw metrics. Tracked against RE:04 / RE:10 in [5-2-3](5-2-3-design-guides-health-modelling.md).

## Already applied

These guides describe decisions DineSafeViz has already made; they're recorded here to show the design is deliberate, not to schedule new work.

### Optimize workload using flows {#flows}

> Source: [Optimize workload design by using flows](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/optimize-workload-using-flows)

- **What the guide covers:** identifying discrete user/system flows, rating each by business criticality, and letting that rating drive independent design and scaling decisions per flow.
- **How it applies to DineSafeViz:** Already in use — the A/B/C flow split with per-flow criticality is precisely this guide's output. It's the connective tissue for the rest of Step 5: the health model, the DR tiers, and the ETL background-job treatment all key off these flow ratings.

### Disaster recovery plan {#disaster-recovery-plan}

> Source: [Develop a disaster recovery (DR) plan for multi-region deployments](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/disaster-recovery)

- **What the guide covers:** building a DR plan from business priorities — defining RPO/RTO, choosing a DR strategy, and planning for wide-scope (regional) failures.
- **How it applies to DineSafeViz:** Already defined. The guide is framed for *multi-region* deployments, which DineSafeViz isn't, but the **planning discipline** transferred: the **passive-cold DR** posture, ≤24h RPO, tiered RTOs, and the manual-DNS-flip holding-page fallback are a deliberately minimal instance of this method — priorities first, then the cheapest recovery mechanism that meets them.

### Background jobs {#background-jobs}

> Source: [Recommendations for developing background jobs](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/background-jobs)

- **What the guide covers:** running work off the request path — batch/scheduled jobs, triggering models, idempotency, and isolating background work so it doesn't degrade the interactive UI.
- **How it applies to DineSafeViz:** Already implemented as the **nightly ETL CronJob** (flow C) — scheduled, off the request path, isolated from the interactive query path on shared B2s burstable capacity. Hardening it further (strict idempotency / safe re-runs) overlaps with the transient-faults backlog item below.

### Continuous integration {#continuous-integration}

> Source: [Recommendations for using continuous integration](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/release-engineering-continuous-integration)

- **What the guide covers:** source control, automated build and test, and integrating changes frequently and safely.
- **How it applies to DineSafeViz:** Already in place via the **GitHub Actions** pipeline and IaC (Terraform/Helm/Helmfile) workflow, at the project's OE Level 1 maturity ([Step 2](2-warch-checklist.md)).

## Backlog

### Handling transient faults {#handling-transient-faults}

> Source: [Recommendations for handling transient faults](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/handle-transient-faults)

- **What the guide covers:** distinguishing temporary failures from real outages and handling them with retries, backoff, and circuit breakers so brief disruptions don't surface as user-visible errors.
- **How it applies to DineSafeViz:** Relevant to the Flask → Postgres connection path and the ETL job, especially given **stop-by-default clusters** and **Spot** eviction — both of which produce exactly the kind of transient, recoverable failure this guide targets. Backlogged: retry/backoff hardening is real work, and it pairs with health modeling (which must tell transient blips apart from true Unhealthy states).

## Not applicable

- **Data partitioning** ([guide](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/partition-data)) — a reliability/scale technique for distributed data. At ~100k rows in a single PostgreSQL instance, there's nothing to partition; introducing it would add complexity with no benefit.
- **Complete a Well-Architected Review assessment** ([guide](https://learn.microsoft.com/en-us/azure/well-architected/design-guides/implementing-recommendations)) — a *process* for consuming assessment output, not an architecture practice. This entire planning series is the equivalent exercise, so the meta-guide is noted rather than adopted.
