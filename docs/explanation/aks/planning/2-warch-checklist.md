# 2. Well-Architected Checklist prioritization

Step 2 of the [WAF suggested learning process](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework#suggested-learning-process):
**prioritize the checklist items relevant to this workload; defer the rest.**

In [Step 1](docs/explanation/aks/planning/1-warch-design-principles.md), we selected which design principles to apply to DineSafeViz. Now we'll prioritize which checklist item to implement first.

- **Phase 1** — now.
- **Phase 2** — a later phase.
- **Phase 3** — a much later phase.
- **N/A** — not applicable.

## Summary

**Phase 1** items prioritized per pillar. Deferred items (Phase 2 / Phase 3 /
N-A) and their rationale are in the pillar tables below.

| Pillar | Phase 1 items | Count |
|---|---|---|
| Reliability | RE:01–07, RE:09, RE:10 | 9 / 10 |
| Security | SE:01–09 | 9 / 12 |
| Cost Optimization | CO:01–14 (all) | 14 / 14 |
| Operational Excellence | OE:01–07, OE:10, OE:11 | 9 / 11 |
| Performance Efficiency | PE:03, PE:07–10 | 5 / 12 |

---

## Reliability - Checklist priority

Source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/checklist

| Code | Recommendation | Priority | Design principle | Backlog | Note |
|---|---|---|---|---|---|
| RE:01 | Simplicity & efficiency | Phase 1 | R5 | — | — |
| RE:02 | Identify & rate flows | Phase 1 | R1 | — | A/B critical, C best-effort (spec.md) |
| RE:03 | Failure mode analysis | Phase 1 | R2 | [FMA](../../backlog/re03-failure-mode-analysis.md) | — |
| RE:04 | Reliability & recovery targets | Phase 1 | R1/R3 | — | RPO/RTO in spec.md |
| RE:05 | Redundancy for critical flows | Phase 1 | R2 | — | multi-AZ + GRS now; data-tier HA → Phase 2 |
| RE:06 | Scaling strategy | Phase 1 | R2 | — | cluster autoscaler now; HPA → Phase 2 |
| RE:07 | Self-preservation / self-healing | Phase 1 | R2/R3 | — | probes, CloudNativePG |
| RE:08 | Resiliency (chaos) testing | Phase 3 | R4 | [failure simulation](../../backlog/re08-failure-simulation.md) | — |
| RE:09 | DR plans (structured, tested) | Phase 1 | R3 | [RB-16](../../backlog/re09-dr-runbook-rb16.md), [drill](../../backlog/re08-recovery-drill.md) | pattern now; RB-16 + drill → Phase 2 |
| RE:10 | Health monitoring & indicators | Phase 1 | R4 | — | Container Insights now; full stack → Phase 3 |

### Reliability - Checklist priority decisions

- **RE:02 — Identify & rate flows**
  - **Q:** Adopt a formal criticality scale (e.g. high/medium/low), or keep the
    binary critical / best-effort split?
  - **A:** Keep the binary split.
    - Only three flows exist (spec.md: A/B critical, C best-effort).
    - A graded scale adds ceremony without changing any operational response
      (R5 simplicity).
- **RE:04 — Reliability & recovery targets**
  - **Q:** Define a **health model** — what signals mark each component healthy?
  - **A:** Health signals per component —
    - Flask: HTTP 200 on `/health` (already implemented).
    - Grafana: HTTP 200 on `/api/health`.
    - Postgres: CloudNativePG instance `ready` (`pg_isready`) with a primary
      elected.
    - Ingress: Standard LB backend healthy behind the static Public IP.
    - The probe parameters that enforce these are RE:07.
  - **Q:** Set informal **SLOs** for flows A/B despite no formal SLA?
  - **A:** No numeric SLO — no SLA and near-zero traffic (spec.md, Phase 1).
    - Informal objective only: "reachable within minutes of cluster start,
      sub-second page loads."
    - A success-rate SLO is unmeasurable without traffic.
- **RE:06 — Scaling strategy**
  - **Q:** What triggers/thresholds drive the cluster autoscaler?
  - **A:** Node-level cluster autoscaler reacting to unschedulable pods (pending
    on CPU/memory requests) — "scale up upon resource contention"
    (arch-design-aks).
    - Pools: `syspool` 1–2, `usrpool` 1–3.
    - No custom % threshold.
    - Per-pod CPU/memory scaling is HPA's job; HPA is deferred to Phase 2.
- **RE:07 — Self-preservation**
  - **Q:** Set liveness/readiness/startup **probe parameters** per workload?
  - **A (revisit post-load-test):** Not set in v1. Starting points:
    - Flask/Grafana: readiness + liveness on the health endpoints, ~10s period,
      3-failure threshold, ~15–30s initial delay.
    - Postgres: rely on CloudNativePG's built-in probes (no manual tuning).
    - Tune after the Phase 2 load test.
  - **Q:** Does Flask implement DB connection **retry/timeout**?
  - **A:** Short connect timeout plus limited retry/backoff on transient DB
    errors.
    - A Postgres pod restart (RTO tier 1) degrades gracefully instead of
      returning 500s.
    - A code-level choice, implemented in Flask's DB layer.
- **RE:10 — Health monitoring**
  - **Q:** Which **SLIs** do we track for A/B, and where are they retained/visible?
  - **A:** Phase 1 SLIs from Container Insights (30-day retention in
    `log-dsv-shared-eus2`):
    - Endpoint/pod availability, HTTP error rate, and request latency for A/B.
    - Postgres metrics via the `postgres_exporter` sidecar.
    - Visible in Azure Monitor now; full operator dashboards → Phase 3 (R4).


## Security - Checklist priority

Source: https://learn.microsoft.com/en-us/azure/well-architected/security/checklist

| Code | Recommendation | Priority | Design principle | Backlog | Note |
|---|---|---|---|---|---|
| SE:01 | Security baseline | Phase 1 | S1/S5 | — | platform defaults now; secure-score/posture → Phase 2 |
| SE:02 | Secure development lifecycle | Phase 1 | S3 | — | light SDL now; image scanning → Phase 2 |
| SE:03 | Data classification | Phase 1 | S2 | — | app data public; secrets sensitive |
| SE:04 | Segmentation & perimeters | Phase 1 | S1 | — | per-env isolation, NetworkPolicy |
| SE:05 | Identity & access management | Phase 1 | S2/S3 | — | Workload Identity, RBAC, OIDC |
| SE:06 | Network traffic isolation | Phase 1 | S2 | — | default-deny now; egress filtering (Firewall) → Phase 2 |
| SE:07 | Encryption | Phase 1 | S2 | — | at rest + at host + TLS |
| SE:08 | Harden resources | Phase 1 | S3/S4 | — | hardening now; PSS-restricted → Phase 2 |
| SE:09 | Protect secrets + rotation | Phase 1 | S1/S2 | — | Key Vault + CSI, rotation workflow |
| SE:10 | Threat monitoring / detection | Phase 2 | S5 | — | no SIEM/Defender in Phase 1 |
| SE:11 | Security testing regimen | Phase 2 | S5 | [image vuln scanning](../../backlog/se11-image-vulnerability-scanning.md) | no pen test |
| SE:12 | Incident response procedures | Phase 2 | S1 | [security IR plan](../../backlog/se12-security-incident-response.md) | — |

### Security - Checklist priority decisions
- **SE:01 — Security baseline**
  - **Q:** Which baseline — Microsoft Cloud Security Benchmark or CIS AKS? How often?
  - **A:** Measure against the **CIS AKS Benchmark** using `kube-bench` (free,
    open-source).
    - MCSB scoring rides Microsoft Defender for Cloud, which is out of scope on
      cost.
    - Run at each AKS version upgrade and on a quarterly cadence.
- **SE:02 — Secure development lifecycle**
  - **Q:** Which SDL scans run in Phase 1?
  - **A:** Free GitHub-native scans in Phase 1:
    - Dependabot (dependency).
    - GitHub secret scanning + push protection (or `gitleaks` in CI).
    - CodeQL SAST (free for public repos; enable if the repo is public).
    - Container image scanning is already backlogged
      ([SE:11](../../backlog/se11-image-vulnerability-scanning.md)).
- **SE:05 — Identity & access**
  - **Q:** MFA / conditional access on the admin (Entra) account?
  - **A:** Enable MFA on the Entra admin account via **security defaults** (free).
    - Conditional Access needs Entra ID P1 (~$6/user/mo) — deferred on cost.
  - **Q:** Granularity of Azure RBAC role assignments per managed identity?
  - **A:** Least-privilege per pod-class identity (arch-design-aks):
    - Each gets only its scoped role — `AcrPull` on ACR, `Key Vault Secrets
      User` on its own environment Key Vault.
    - No cross-environment assignment.
    - A separate control-plane identity per environment.
- **SE:08 — Harden resources**
  - **Q:** Pod Security Standards level for Phase 1 — baseline or restricted?
  - **A:** Baseline (default) profile in Phase 1; **Restricted** deferred
    to Phase 2 (arch-design-aks conformance table).
  - **Q:** Disable AKS local accounts? Confirm API-server authorized IP ranges.
  - **A:** Disable local accounts (`--disable-local-accounts`, Entra-only):
    - Free hardening; Workload Identity/OIDC is already the auth path.
    - API-server authorized IP ranges are confirmed in v1 (workstation + GHA
      runner ranges).
- **SE:09 — Protect secrets + rotation**
  - **Q:** Rotation cadence for DB credentials and TLS certs — automated or manual?
  - **A:** Split by secret type —
    - TLS certs: automated via cert-manager/ACME (Let's Encrypt ~90-day certs);
      a monthly cert-renewal heartbeat forces a start to prevent expiry.
    - DB credentials: stored in Key Vault, surfaced via CSI; rotated via an
      on-demand rotation workflow (runbook) plus an annual scheduled rotation.

## Cost Optimization - Checklist priority

Source: https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/checklist

| Code | Recommendation | Priority | Design principle | Backlog | Note |
|---|---|---|---|---|---|
| CO:01 | Culture of financial responsibility | Phase 1 | C1 | — | — |
| CO:02 | Cost model | Phase 1 | C1 | — | — |
| CO:03 | Collect & review cost data | Phase 1 | C5 | [review cadence](../../backlog/co03-cost-alert-review-cadence.md) | alerts now |
| CO:04 | Spending guardrails | Phase 1 | C2 | — | budget alerts + auto-shutdown |
| CO:05 | Best rates from providers | Phase 1 | C4 | — | spot, cheapest NA region, no reservations |
| CO:06 | Align usage to billing increments | Phase 1 | C3/C4 | — | burstable + stop-by-default |
| CO:07 | Optimize component costs | Phase 1 | C5 | — | remove unused; ACR cleanup |
| CO:08 | Optimize environment costs | Phase 1 | C2 | — | prod/stg stopped by default |
| CO:09 | Optimize flow costs | Phase 1 | C4 | — | — |
| CO:10 | Optimize data costs | Phase 1 | — | — | storage: Standard HDD, LRS/GRS split, retention |
| CO:11 | Optimize code costs | Phase 1 | — | — | single ETL CronJob; direct SQL |
| CO:12 | Optimize scaling costs | Phase 1 | C3 | — | autoscaler + spot |
| CO:13 | Optimize personnel time | Phase 1 | O4 | — | automation reduces toil |
| CO:14 | Consolidate resources | Phase 1 | C4 | — | one cluster hosts all workloads |

### Cost Optimization - Checklist priority decisions

- **CO:02 — Cost model**
  - **Q:** Produce a consolidated per-resource monthly cost estimate?
  - **A:** Consolidated figures in [spec.md](../../../ref/spec.md):
    - AKS Free saves ~$73/mo per cluster
    - static PIP ~$4/mo vs AGW ~$30/mo
    - no Azure Firewall saves ~$30/mo
    - passive-cold DR ~$2/mo
    - GRS staging ~$1/mo uplift
    - self-hosted Postgres avoids ~$15–20/mo
    - Steady-state stays $25–50/mo within the $100 cap. (Follow-up doc task.)
    
- **CO:08 — Optimize environment costs**
  - **Q:** Right-size staging below prod, or keep parity for production fidelity?
  - **A:** Keep node-pool parity (same B2s, same autoscale bounds):
    - Stop-by-default drives idle cost to ~zero, so parity is nearly free and
      preserves prod fidelity.
    - But size the staging Postgres `Cluster` requests below prod (prod is
      250m CPU / 512Mi). Confirm.
- **CO:10 — Optimize data costs**
  - **Q:** Retention windows — Log Analytics, WAL/basebackup, ACR images?
  - **A:** Retention values (recorded in spec.md):
    - Log Analytics — 30 days.
    - ACR — untagged-image cleanup workflow already runs.
    - WAL/basebackup — a 7-day PITR window (daily basebackup + continuous WAL),
      which comfortably covers the ≤24h RPO.

## Operational Excellence - Checklist priority

Source: https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/checklist

| Code | Recommendation | Priority | Design principle | Backlog | Note |
|---|---|---|---|---|---|
| OE:01 | Standard practices / DevOps culture | Phase 1 | O1 | — | solo scale |
| OE:02 | Standardize operations (routine/emergency) | Phase 1 | O1/O5 | [AKS upgrade runbook](../../backlog/oe02-aks-upgrade-runbook.md) | runbook catalog |
| OE:03 | Formalize development practices | Phase 1 | O2 | — | lightweight, solo |
| OE:04 | Tools, QA, source control, style | Phase 1 | O2 | — | — |
| OE:05 | Infrastructure as Code | Phase 1 | O5 | — | Terraform + Helm/Helmfile |
| OE:06 | Workload supply chain / pipelines | Phase 1 | O5 | — | GHA now; e2e tests → Phase 2 |
| OE:07 | Monitoring stack | Phase 1 | O3 | — | baseline now; full stack → Phase 3 |
| OE:08 | Incident management | Phase 2 | O1/S1 | [incident-review](../../backlog/oe08-incident-review-process.md) | — |
| OE:09 | Testing | Phase 2 | O2 | — | synthetic e2e |
| OE:10 | Automation (reliable, secure) | Phase 1 | O4 | — | core strength |
| OE:11 | Safe deployment practices | Phase 1 | O5 | — | pipelines + approval gate; progressive rollout minimal |

### Operational Excellence - Checklist priority decisions

- **OE:02 — Standardize operations**
  - **Q:** Runbook template/format, and which runbooks beyond the current catalog?
  - **A:** Adopt a standard template:
    - Sections: Purpose / Trigger / Prerequisites / Steps / Verification /
      Rollback / Escalation.
    - Catalog = RB-01…RB-16.
    - Known gap: an AKS version-upgrade runbook (backlogged
      [OE:02](../../backlog/oe02-aks-upgrade-runbook.md)).
- **OE:03 / OE:04 — Development practices & tooling**
  - **Q:** Branching strategy, PR/commit conventions, pre-commit linters?
  - **A:** Lightweight, solo-scale practices:
    - Short-lived feature branches off `main` with PR + squash merge (audit
      trail; solo, so self-review).
    - Conventional Commits.
    - CI / pre-commit linters, all free OSS: `tflint`, `hadolint`,
      `markdownlint`, plus `terraform fmt`.
- **OE:06 — Workload supply chain**
  - **Q:** Pipeline stages + quality gates, and the promotion path stg → prod?
  - **A:** Pipeline: build → lint/test → build image → push to ACR → deploy to
    `stg` → **GitHub Environments approval gate** → deploy the same image digest
    to `prod`.
    - The immutable image is promoted by digest (no rebuild between environments).
- **OE:09 — Testing**
  - **Q:** Which tests run in CI in Phase 1, and are they release gates?
  - **A:** Phase 1 CI:
    - Unit tests for Flask + ETL and the linters run as **required gates**.
    - Integration and synthetic e2e tests are deferred to Phase 2
      (arch-design-aks).
- **OE:11 — Safe deployment**
  - **Q:** Deployment strategy (rolling vs. recreate) and a rollback procedure?
  - **A:** Strategy by component, with layered rollback:
    - Stateless (Flask/Grafana): Helm rolling update (default `RollingUpdate`).
    - Postgres: single instance, so a version change is a brief recreate (short
      downtime acceptable given stop-by-default).
    - Rollback: `helm rollback`; infra via Terraform reprovision; regional
      failure via the DR runbook (RB-16, backlogged).

## Performance Efficiency - Checklist priority

Source: https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/checklist

| Code | Recommendation | Priority | Design principle | Backlog | Note |
|---|---|---|---|---|---|
| PE:01 | Define performance targets | Phase 2 | P1 | — | loose by design; connection target TBD (spec.md) |
| PE:02 | Capacity planning | Phase 2 | P2 | — | vertical scaling if needed |
| PE:03 | Select the right services | Phase 1 | P2 | — | AKS/Postgres/SSD chosen (tech-choices) |
| PE:04 | Consistent performance measurement | Phase 3 | P3 | — | baseline metrics only in Phase 1 |
| PE:05 | Optimize scaling & partitioning | Phase 2 | P2 | — | autoscaler now; HPA → Phase 2 |
| PE:06 | Performance testing | Phase 2 | P3 | — | k6 load test |
| PE:07 | Optimize code & infrastructure | Phase 1 | P3 | — | offload to platform; right-sized |
| PE:08 | Optimize data usage | Phase 1 | P2 | — | indexes on filtered columns |
| PE:09 | Prioritize critical-flow performance | Phase 1 | P1 | — | flows A/B identified |
| PE:10 | Optimize operational tasks | Phase 1 | — | — | backups, rotation, deploy impact |
| PE:11 | Respond to live performance issues | Phase 3 | P3 | — | — |
| PE:12 | Continuously optimize | Phase 3 | P4 | — | — |

### Performance Efficiency - Checklist priority decisions

- **PE:01 — Define performance targets**
  - **Q:** Concurrent-connections target (spec.md TBD) and a query budget for A/B?
  - **A:** Matched to a genuine solo/portfolio-demo load (recorded in spec.md,
    closes the prior TBD):
    - **~10 concurrent connections** (sizes Postgres `max_connections` and Flask
      worker/pool counts).
    - **Sub-second (<1s) query budget** for flows A/B.
- **PE:07 — Optimize code & infrastructure**
  - **Q:** Postgres tuning and Flask worker / connection-pool sizing?
  - **A (revisit post-load-test):** Only "basic tuning" is noted in v1. Phase 1
    starting points on B2s (2 vCPU / 4 GiB; Postgres request 512Mi):
    - `shared_buffers` ~128–256MB, `work_mem` ~4MB.
    - `max_connections` ~25–30 (headroom over the ~10 target in PE:01, covering
      the Flask pool plus admin/replication connections).
    - Flask: 2–4 gunicorn workers with a small SQLAlchemy pool.
    - Tune after the Phase 2 load test.
- **PE:08 — Optimize data usage**
  - **Q:** Index design — which columns get secondary indexes?
  - **A:** Secondary indexes on commonly filtered/joined columns
    (arch-design-planning):
    - Establishment ID and inspection date.
    - The `inspections`→`establishments` and `infractions`→`inspections` foreign
      keys.
    - Infraction severity if filtered.
    - Primary keys are already indexed.
