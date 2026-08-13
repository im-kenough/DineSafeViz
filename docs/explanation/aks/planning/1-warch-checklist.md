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
task.

Each question now carries an **A:** answer sourced from the v1
[design-planning](../../../0-needs-review/ref/arch/design-planning/) docs and
[spec.md](../../../ref/spec.md). All items are **Decided**; two variants apply:

- **Decided** — resolved from v1 material, a step-1 decision, or an operator
  choice recorded here.
- **Decided — starting point, revisit post-load-test** — a tuning value (probe
  timings, Postgres/Flask sizing) set to a sensible P1 default, to be confirmed
  against the P2 load test rather than guessed precisely now.

## Reliability — open decisions

- **RE:02 — Identify & rate flows**
  - Q: Adopt a formal criticality scale (e.g. high/medium/low), or keep the
    binary critical / best-effort split?
  - **A (Decided):** Keep the binary split. Only three flows exist (spec.md:
    A/B critical, C best-effort); a graded scale adds ceremony without changing
    any operational response (R5 simplicity).
- **RE:04 — Reliability & recovery targets**
  - Q: Define a **health model** — what signals mark each component healthy?
  - **A (Decided):** Health signals per component —
    - Flask: HTTP 200 on `/health` (already implemented).
    - Grafana: HTTP 200 on `/api/health`.
    - Postgres: CloudNativePG instance `ready` (`pg_isready`) with a primary
      elected.
    - Ingress: Standard LB backend healthy behind the static Public IP.
    - The probe parameters that enforce these are RE:07.
  - Q: Set informal **SLOs** for flows A/B despite no formal SLA?
  - **A (Decided):** No numeric SLO — no SLA and near-zero traffic (spec.md,
    P1). Informal objective only: "reachable within minutes of cluster start,
    sub-second page loads." A success-rate SLO is unmeasurable without traffic.
- **RE:06 — Scaling strategy**
  - Q: What triggers/thresholds drive the cluster autoscaler?
  - **A (Decided):** The cluster autoscaler is node-level and reacts to
    unschedulable pods (pending on CPU/memory requests) — "scale up upon
    resource contention" (arch-design-aks). Pools: `syspool` 1–2, `usrpool`
    1–3. No custom % threshold; per-pod CPU/memory scaling is HPA's job, and
    HPA is deferred to P2.
- **RE:07 — Self-preservation**
  - Q: Set liveness/readiness/startup **probe parameters** per workload?
  - **A (Decided — starting point, revisit post-load-test):** Not set in v1.
    Starting points — Flask/Grafana: readiness + liveness on the health
    endpoints, ~10s period, 3-failure threshold, ~15–30s initial delay;
    Postgres: rely on CloudNativePG's built-in probes (no manual tuning). Tune
    after the P2 load test.
  - Q: Does Flask implement DB connection **retry/timeout**?
  - **A (Decided):** Adopt a short connect timeout plus limited retry/backoff on
    transient DB errors so a Postgres pod restart (RTO tier 1) degrades
    gracefully instead of returning 500s. A code-level choice, implemented in
    Flask's DB layer.
- **RE:10 — Health monitoring**
  - Q: Which **SLIs** do we track for A/B, and where are they retained/visible?
  - **A (Decided):** P1 SLIs from Container Insights (30-day retention in
    `log-dsv-shared-eus2`): endpoint/pod availability, HTTP error rate, and
    request latency for A/B; Postgres metrics via the `postgres_exporter`
    sidecar. Visible in Azure Monitor now; full operator dashboards → Phase 3
    (R4).

## Security — open decisions

- **SE:01 — Security baseline**
  - Q: Which baseline — Microsoft Cloud Security Benchmark or CIS AKS? How often?
  - **A (Decided):** Measure against the **CIS AKS Benchmark** using
    `kube-bench` (free, open-source). MCSB scoring rides Microsoft Defender for
    Cloud, which is out of scope on cost. Run at each AKS version upgrade and on
    a quarterly cadence.
- **SE:02 — Secure development lifecycle**
  - Q: Which SDL scans run in P1?
  - **A (Decided):** Free GitHub-native scans in P1 — Dependabot (dependency),
    GitHub secret scanning + push protection (or `gitleaks` in CI), and CodeQL
    SAST (free for public repos; enable if the repo is public). Container image
    scanning is already backlogged
    ([SE:11](../../backlog/se11-image-vulnerability-scanning.md)).
- **SE:05 — Identity & access**
  - Q: MFA / conditional access on the admin (Entra) account?
  - **A (Decided):** Enable MFA on the Entra admin account via **security
    defaults** (free). Conditional Access needs Entra ID P1 (~$6/user/mo) —
    deferred on cost.
  - Q: Granularity of Azure RBAC role assignments per managed identity?
  - **A (Decided):** Least-privilege per pod-class identity (arch-design-aks):
    each gets only its scoped role — `AcrPull` on ACR, `Key Vault Secrets User`
    on its own environment Key Vault; no cross-environment assignment. A
    separate control-plane identity per environment.
- **SE:08 — Harden resources**
  - Q: Pod Security Standards level for P1 — baseline or restricted?
  - **A (Decided):** Baseline (default) profile in P1; **Restricted** deferred
    to P2 (arch-design-aks conformance table).
  - Q: Disable AKS local accounts? Confirm API-server authorized IP ranges.
  - **A (Decided):** Disable local accounts (`--disable-local-accounts`,
    Entra-only) — free hardening; Workload Identity/OIDC is already the auth
    path. API-server authorized IP ranges are confirmed in v1 (workstation +
    GHA runner ranges).
- **SE:09 — Protect secrets + rotation**
  - Q: Rotation cadence for DB credentials and TLS certs — automated or manual?
  - **A (Decided):** TLS certs — automated via cert-manager/ACME (Let's Encrypt
    ~90-day certs); a monthly cert-renewal heartbeat forces a start to prevent
    expiry. DB credentials — stored in Key Vault, surfaced via CSI; rotated via
    an on-demand rotation workflow (runbook) plus an annual scheduled rotation.

## Cost Optimization — open decisions

- **CO:02 — Cost model**
  - Q: Produce a consolidated per-resource monthly cost estimate in spec.md?
  - **A (Decided):** Yes — consolidate the figures already scattered in v1
    into one table in [spec.md](../../../ref/spec.md): AKS Free saves ~$73/mo
    per cluster; static PIP ~$4/mo vs AGW ~$30/mo; no Azure Firewall saves
    ~$30/mo; passive-cold DR ~$2/mo; GRS staging ~$1/mo uplift; self-hosted
    Postgres avoids ~$15–20/mo. Steady-state stays $25–50/mo within the $100
    cap. (Follow-up doc task.)
- **CO:08 — Optimize environment costs**
  - Q: Right-size staging below prod, or keep parity for production fidelity?
  - **A (Decided):** Keep node-pool parity (same B2s, same autoscale bounds) —
    stop-by-default drives idle cost to ~zero, so parity is nearly free and
    preserves prod fidelity — but size the staging Postgres `Cluster` requests
    below prod (prod is 250m CPU / 512Mi). Confirm.
- **CO:10 — Optimize data costs**
  - Q: Retention windows — Log Analytics, WAL/basebackup, ACR images?
  - **A (Decided):** Log Analytics — 30 days. ACR — untagged-image cleanup
    workflow already runs. WAL/basebackup — a 7-day PITR window (daily
    basebackup + continuous WAL), which comfortably covers the ≤24h RPO.
    Retention values recorded in spec.md.

## Operational Excellence — open decisions

- **OE:02 — Standardize operations**
  - Q: Runbook template/format, and which runbooks beyond the current catalog?
  - **A (Decided):** Adopt a standard template — Purpose / Trigger /
    Prerequisites / Steps / Verification / Rollback / Escalation. Catalog =
    RB-01…RB-16; the known gap is an AKS version-upgrade runbook (backlogged
    [OE:02](../../backlog/oe02-aks-upgrade-runbook.md)).
- **OE:03 / OE:04 — Development practices & tooling**
  - Q: Branching strategy, PR/commit conventions, pre-commit linters?
  - **A (Decided):** Short-lived feature branches off `main` with PR + squash
    merge (audit trail; solo, so self-review). Conventional Commits. CI /
    pre-commit linters, all free OSS: `tflint`, `hadolint`, `markdownlint`, plus
    `terraform fmt`.
- **OE:06 — Workload supply chain**
  - Q: Pipeline stages + quality gates, and the promotion path stg → prod?
  - **A (Decided):** build → lint/test → build image → push to ACR → deploy to
    `stg` → **GitHub Environments approval gate** → deploy the same image digest
    to `prod`. The immutable image is promoted by digest (no rebuild between
    environments).
- **OE:09 — Testing**
  - Q: Which tests run in CI in P1, and are they release gates?
  - **A (Decided):** P1 CI runs unit tests for Flask + ETL and the linters as
    **required gates**; integration and synthetic e2e tests are deferred to P2
    (arch-design-aks).
- **OE:11 — Safe deployment**
  - Q: Deployment strategy (rolling vs. recreate) and a rollback procedure?
  - **A (Decided):** Stateless (Flask/Grafana) — Helm rolling update (default
    `RollingUpdate`). Postgres — single instance, so a version change is a brief
    recreate (short downtime acceptable given stop-by-default). Rollback via
    `helm rollback`; infra via Terraform reprovision; regional failure via the
    DR runbook (RB-16, backlogged).

## Performance Efficiency — open decisions

- **PE:01 — Define performance targets**
  - Q: Concurrent-connections target (spec.md TBD) and a query budget for A/B?
  - **A (Decided):** **~10 concurrent connections** (sizes Postgres
    `max_connections` and Flask worker/pool counts) and a **sub-second (<1s)
    query budget** for flows A/B — matched to a genuine solo/portfolio-demo
    load. Recorded in spec.md (closes the prior TBD).
- **PE:07 — Optimize code & infrastructure**
  - Q: Postgres tuning and Flask worker / connection-pool sizing?
  - **A (Decided — starting point, revisit post-load-test):** Only "basic
    tuning" is noted in v1. P1 starting points on B2s (2 vCPU / 4 GiB; Postgres
    request 512Mi): `shared_buffers` ~128–256MB, `work_mem` ~4MB,
    `max_connections` ~25–30 (headroom over the ~10 target in PE:01, covering
    the Flask pool plus admin/replication connections). Flask: 2–4 gunicorn
    workers with a small SQLAlchemy pool. Tune after the P2 load test.
- **PE:08 — Optimize data usage**
  - Q: Index design — which columns get secondary indexes?
  - **A (Decided):** Secondary indexes on commonly filtered/joined columns
    (arch-design-planning): establishment ID and inspection date, plus the
    `inspections`→`establishments` and `infractions`→`inspections` foreign keys,
    and infraction severity if filtered. Primary keys are already indexed.
