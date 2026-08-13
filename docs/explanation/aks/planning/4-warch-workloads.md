# 4. Match workload scenarios

Step 4 of the [Well Architected Framework process](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework#suggested-learning-process):
find a published [workload guide](https://learn.microsoft.com/en-us/azure/well-architected/workloads)
that matches your scenario and follow its design methodology.

A workload guide is an **overlay** on the five pillars, tuned for a whole
*class* of workload. It re-ranks the pillars for that class, names class-specific
design areas, and highlights the considerations that matter most — so you don't
rediscover them yourself.

## Summary

Microsoft publishes workload guides for the types below, but **none are
applicable to DineSafeViz**. DineSafeViz is a small, single-tenant,
budget-capped portfolio web app on AKS with near-zero traffic and no SLA — it
does not fit any published class. Each guide, and why it doesn't apply, follows.

The AKS-specific design guidance DineSafeViz *does* use isn't a workload guide at
all; it lives in the **service guides / AKS baseline reference architecture**,
which is [Step 5](5-1-warch-service-guides.md).

## Workload types

### [AI](https://learn.microsoft.com/en-us/azure/well-architected/ai/get-started)

- **What it is:**
  - Built around predictive, discriminative, or generative AI, where models
    (GPT-style language models, classifiers) become first-class components.
  - Replaces deterministic logic with nondeterministic model behaviour.
  - Distinctive concerns: model build-vs-buy, training and grounding data,
    MLOps/GenAIOps, model decay, and responsible-AI ethics.
- **Why it's not applicable:**
  - DineSafeViz has no AI component — it reads public DineSafe records from
    Postgres and renders them through Flask and Grafana.
  - Fully deterministic SQL: no models, no inference, no training data.

### [SaaS](https://learn.microsoft.com/en-us/azure/well-architected/saas/get-started)

- **What it is:**
  - A commercial software-as-a-service product run by an ISV and sold to
    businesses (B2B) or consumers (B2C).
  - Centres on multitenancy — sharing infrastructure across paying customers
    while guaranteeing per-tenant isolation, security, and performance.
  - Adds billing/COGS management and operating at scale.
- **Why it's not applicable:**
  - DineSafeViz is single-tenant and non-commercial — no customers, no tenant
    isolation, no billing.
  - No scale or growth target: it's shown to employers on demand, not sold.

### [Mission-critical](https://learn.microsoft.com/en-us/azure/well-architected/mission-critical/mission-critical-overview)

- **What it is:**
  - A workload where unavailability carries significant financial
    (business-critical) or human (safety-critical) cost, so it must always be
    available.
  - Assumes high engineering rigour and failure-resilient distributed design.
  - Typically multi-region active/active, accepting large cost tradeoffs to buy
    reliability.
- **Why it's not applicable:**
  - DineSafeViz is the deliberate inverse: no SLA, clusters stopped by default,
    single-region, and spend capped at $100/mo.
  - Flows A/B fall back to a static holding page rather than justifying
    always-on cost ([Step 3](3-warch-tradeoffs.md)).
  - Useful only as a contrast that validates those choices.

### [HPC (high-performance computing)](https://learn.microsoft.com/en-us/azure/well-architected/hpc/get-started-overview)

- **What it is:**
  - Compute-intensive workloads — large-scale simulation, modeling, or analysis.
  - Need far more processing, memory, and I/O than a normal system can provide.
  - Achieved through massive parallelism across many CPUs, GPUs, or nodes (with
    schedulers like Slurm, fast interconnects, and parallel file systems).
- **Why it's not applicable:**
  - DineSafeViz does no parallel or compute-heavy work.
  - Its heaviest task is a nightly single-CronJob ETL over ~100k rows on a B2s
    burstable node — the opposite of the specialized parallel hardware HPC
    targets.

### [Sustainability](https://learn.microsoft.com/en-us/azure/well-architected/sustainability/overview)

- **What it is:**
  - A cross-cutting *lens*, not a distinct workload class.
  - Minimizes a workload's energy use and carbon emissions — right-sizing,
    killing idle infrastructure, trimming excess telemetry and replication.
  - Overlaps heavily with the Cost Optimization pillar.
- **Why it's not applicable:**
  - It isn't a scenario to match, so there's nothing to adopt as a class guide.
  - DineSafeViz's cost decisions already align with it incidentally —
    stop-by-default clusters, spot/burstable VMs, 30-day log retention, and one
    consolidated cluster all cut waste as a side effect of the budget cap.
