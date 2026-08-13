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
| RE:03 | Failure mode analysis | P1 | R2 — [FMA](../../backlog/re03-failure-mode-analysis.md) |
| RE:04 | Reliability & recovery targets | P1 | R1/R3 — RPO/RTO in spec.md |
| RE:05 | Redundancy for critical flows | P1 | R2 — multi-AZ + GRS now; data-tier HA → P2 |
| RE:06 | Scaling strategy | P1 | R2 — cluster autoscaler now; HPA → P2 |
| RE:07 | Self-preservation / self-healing | P1 | R2/R3 — probes, CloudNativePG |
| RE:08 | Resiliency (chaos) testing | P3 | R4 — [failure simulation](../../backlog/re08-failure-simulation.md) |
| RE:09 | DR plans (structured, tested) | P1 | R3 — pattern now; [RB-16](../../backlog/re09-dr-runbook-rb16.md) + [drill](../../backlog/re08-recovery-drill.md) → P2 |
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
| SE:11 | Security testing regimen | P2 | S5 — [image vuln scanning](../../backlog/se11-image-vulnerability-scanning.md); no pen test |
| SE:12 | Incident response procedures | P2 | S1 — [security IR plan](../../backlog/se12-security-incident-response.md) |

## Cost Optimization

Source: https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/checklist

| Code | Recommendation | Priority | Maps to / note |
|---|---|---|---|
| CO:01 | Culture of financial responsibility | P1 | C1 |
| CO:02 | Cost model | P1 | C1 |
| CO:03 | Collect & review cost data | P1 | C5 — alerts now; [review cadence](../../backlog/co03-cost-alert-review-cadence.md) |
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
| OE:02 | Standardize operations (routine/emergency) | P1 | O1/O5 — runbook catalog; [AKS upgrade runbook](../../backlog/oe02-aks-upgrade-runbook.md) |
| OE:03 | Formalize development practices | P1 | O2 — lightweight, solo |
| OE:04 | Tools, QA, source control, style | P1 | O2 |
| OE:05 | Infrastructure as Code | P1 | O5 — Terraform + Helm/Helmfile |
| OE:06 | Workload supply chain / pipelines | P1 | O5 — GHA now; e2e tests → P2 |
| OE:07 | Monitoring stack | P1 | O3 — baseline now; full stack → P3 |
| OE:08 | Incident management | P2 | O1/S1 — [incident-review](../../backlog/oe08-incident-review-process.md) |
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

---

# Open decisions surfaced by the checklist

Reading each checklist item's detail, most are fully resolved by the step-1
decisions in [0-warch-design-principles.md](0-warch-design-principles.md). The
items below raise **new, implementation-level decisions** not yet made. Items
not listed are already covered by step 1 or by a [backlog](../../backlog/README.md)
task. These are questions to answer in a later decision pass — not yet decided.

## Reliability — open decisions

- **RE:02 — Identify & rate flows**
  - Adopt a formal criticality scale (e.g. high/medium/low), or keep the binary
    critical / best-effort split?
- **RE:04 — Reliability & recovery targets**
  - Define a **health model**: what signals mark each component (Flask, Grafana,
    Postgres, ingress) healthy vs. unhealthy?
  - Set informal **SLOs** for flows A/B (e.g. success rate) despite having no
    formal SLA?
- **RE:06 — Scaling strategy**
  - What triggers/thresholds drive the cluster autoscaler (CPU/memory %, node
    pressure)?
- **RE:07 — Self-preservation**
  - Set liveness/readiness/startup **probe parameters** per workload?
  - Does Flask implement DB connection **retry/timeout** (transient-fault
    handling)?
- **RE:10 — Health monitoring**
  - Which **SLIs** (uptime, error rate, latency) do we track for A/B, and where
    are they retained/visible?

## Security — open decisions

- **SE:01 — Security baseline**
  - Which baseline do we measure against — Microsoft Cloud Security Benchmark or
    CIS AKS benchmark? How often?
- **SE:02 — Secure development lifecycle**
  - Which SDL scans run in P1 — dependency scanning (Dependabot), secret
    scanning (GitHub secret scanning / gitleaks), SAST? (image scanning is
    already backlogged as [SE:11](../../backlog/se11-image-vulnerability-scanning.md))
- **SE:05 — Identity & access**
  - MFA / conditional access on the admin (Entra) account?
  - Granularity of Azure RBAC role assignments per managed identity?
- **SE:08 — Harden resources**
  - Pod Security Standards level for P1 — baseline or restricted?
  - Disable AKS local accounts (Entra-only auth)? Confirm API-server authorized
    IP ranges.
- **SE:09 — Protect secrets + rotation**
  - Rotation cadence for DB credentials and TLS certs — automated or manual?

## Cost Optimization — open decisions

- **CO:02 — Cost model**
  - Produce a consolidated per-resource monthly cost estimate (in
    [spec.md](../../../ref/spec.md))?
- **CO:08 — Optimize environment costs**
  - Right-size staging below prod (smaller SKU / fewer nodes), or keep parity
    for production fidelity?
- **CO:10 — Optimize data costs**
  - Retention windows: Log Analytics (30d set), WAL/basebackup retention, ACR
    image retention?

## Operational Excellence — open decisions

- **OE:02 — Standardize operations**
  - Runbook template/format, and which runbooks beyond the current catalog?
- **OE:03 / OE:04 — Development practices & tooling**
  - Branching strategy (trunk-based vs. GitFlow), PR/commit conventions, and
    pre-commit linters (tflint, hadolint, markdownlint)?
- **OE:06 — Workload supply chain**
  - Pipeline stages + quality gates, and the artifact promotion path stg → prod?
- **OE:09 — Testing**
  - Which tests run in CI in P1 (unit/integration for Flask + ETL), and are they
    release gates?
- **OE:11 — Safe deployment**
  - Deployment strategy (rolling vs. recreate) and a documented rollback
    procedure?

## Performance Efficiency — open decisions

- **PE:01 — Define performance targets**
  - Set the concurrent-connections target (currently TBD in
    [spec.md](../../../ref/spec.md)) and a sub-second query budget for A/B?
- **PE:07 — Optimize code & infrastructure**
  - Postgres tuning (`shared_buffers`, `work_mem`, `max_connections`) and Flask
    worker / connection-pool sizing?
- **PE:08 — Optimize data usage**
  - Index design — which columns get secondary indexes (establishment ID,
    inspection date)?
