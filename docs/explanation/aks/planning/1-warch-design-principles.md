# 1. Well-Architected Design Principles

This document reviews each pillar and their design principles. Each principle will be reviewed to decide if it should be incoporated into this project.

- **Adopt** — implement the approach as recommended.
- **Adapt** — implement a lighter/modified version (state how).
- **Defer** — valid but postponed to a later phase (state which).
- **N/A** — not applicable to this workload (state why).

## Summary

High-level decision per design principle. Details in the pillar sections below.

### Reliability

| ID | Design principle | Decision |
|---|---|---|
| R1 | Design for business requirements | Adopt |
| R2 | Design for resilience | Adapt |
| R3 | Design for recovery | Adopt |
| R4 | Design for operations | Split (adopt automation / defer observability) |
| R5 | Keep it simple | Adopt |

### Security

| ID | Design principle | Decision |
|---|---|---|
| S1 | Plan your security readiness | Adapt |
| S2 | Design to protect confidentiality | Adopt |
| S3 | Design to protect integrity | Adapt |
| S4 | Design to protect availability | Adapt |
| S5 | Sustain and evolve your security posture | Defer (mostly) |

### Cost Optimization

| ID | Design principle | Decision |
|---|---|---|
| C1 | Develop cost-management discipline | Adopt |
| C2 | Design with a cost-efficiency mindset | Adopt |
| C3 | Design for usage optimization | Adopt (adapted) |
| C4 | Design for rate optimization | Adopt |
| C5 | Monitor and optimize over time | Adopt |

### Operational Excellence

| ID | Design principle | Decision |
|---|---|---|
| O1 | Embrace DevOps culture | Adapt |
| O2 | Establish development standards | Adapt |
| O3 | Evolve operations with observability | Split (baseline now / full to Phase 3) |
| O4 | Automate for efficiency | Adopt |
| O5 | Adopt safe deployment practices | Adopt (adapted) |

### Performance Efficiency

| ID | Design principle | Decision |
|---|---|---|
| P1 | Negotiate realistic performance targets | Adapt |
| P2 | Design to meet capacity requirements | Adapt |
| P3 | Achieve and sustain performance | Defer |
| P4 | Optimize for long-term improvement | Defer |

---

## Reliability

Source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/principles

### R1. Design for business requirements

> Get clarity on the workload's scope, user growth, and the promises made to
> external customers and internal stakeholders.

- **Required levels / "good enough"?**
  - Portfolio demo; clusters **stopped by default**, started on demand.
  - Good enough = "reachable when started"; **no 24/7 availability**.
  - Resiliency: pod-level self-healing only (Phase 1). Recovery: passive-cold.
  - Observability: deferred to Phase 3. Simplicity: heavily prioritized.
- **Constraints?**
  - Cost: **$100/mo hard cap**, $25–50 steady-state.
  - Compliance: none (public open data). Latency: no strict target.
  - Geography: **North America**; specific region chosen at implementation by cost.
- **Trade-offs accepted?**
  - Reduced Reliability (single Postgres, no HA, no HPA, no SLA) for **cost** + **simplicity**, while still demonstrating passive-cold DR.
- **Reliability outcome per critical flow?**
  - Flow A (Flask) + B (Grafana): **critical** → degrade to holding page via manual DNS flip.
  - Flow C (ETL refresh): **best-effort** — a missed refresh is acceptable.
- **Usage / growth?**
  - Near-zero real traffic; no growth expected. Dataset ~100k rows, grows slowly.
- **External dependencies?**
  - Toronto Open Data feed, Let's Encrypt/ACME, Azure platform, GitHub Actions.
  - Single subscription/owner — no org constraints. Bound Flow C + cert renewal, not A/B.

**Decision: Adopt** (demo scope). Values pinned in [spec.md](../../../ref/spec.md).

### R2. Design for resilience

> The workload must continue to operate with full or reduced functionality.

- **Critical path vs. degraded?**
  - Critical path = nginx → Flask/Grafana → PostgreSQL (stateful critical component).
  - ETL CronJob is **non-critical** (Flow C).
- **Failure points / effect?**
  - Postgres pod fail → CloudNativePG restart + PVC re-mount (RTO tier 1).
  - Node fail → reschedule. Zone/region outage → passive-cold DR (RTO tier 2).
  - Ingress restart → survives via static Public IP.
  - Backlog: [Failure Mode Analysis](../../backlog/failure-mode-analysis.md) not yet done.
- **Self-preservation?**
  - Health probes, `postgres_exporter` sidecar, nginx gateway offload/route, Cilium default-deny NetworkPolicy.
- **Scale out?**
  - Cluster autoscaler (`syspool` 1–2, `usrpool` 1–3), multi-AZ-capable pools.
  - No HPA in Phase 1 (no traffic to justify it).
- **Redundancy in layers?**
  - Multi-AZ pool defs (min 1); GRS = cross-region data copy; passive-cold = active-passive.
  - **Single-instance Postgres = no data-tier HA** (multi-replica → Phase 2).
- **Overprovision?**
  - No — burstable B2s, spot user pool, min-1 pools. Risk accepted (zero traffic).

**Decision: Adapt** — resilience deliberately minimized for cost.

### R3. Design for recovery

> The workload must anticipate and recover from failures of all magnitudes with
> minimal disruption.

- **Recovery plans / drills?**
  - Passive-cold DR pattern documented; RPO ≤ 24h / two-tier RTO in [spec.md](../../../ref/spec.md).
  - Backlog: [DR runbook RB-16](../../backlog/dr-runbook-rb16.md), [recovery drill](../../backlog/recovery-drill.md).
- **Repair data within targets?**
  - CloudNativePG WAL archive + daily basebackup to GRS; PITR via Barman.
  - Weekly backup-verification workflow (issues on stale backup).
  - Backlog: [backup immutability](../../backlog/backup-immutability.md).
- **Automated self-healing?**
  - CloudNativePG pod restart / PVC re-mount; K8s probes restart unhealthy pods.
- **Immutable ephemeral units?**
  - Stateless Flask/Grafana as immutable images via Helm; environments reprovisionable from IaC.

**Decision: Adopt**

### R4. Design for operations

> Shift left in operations to anticipate failure conditions.

- **Observable systems?**
  - Phase 1: Container Insights + Azure Monitor (30-day retention); `postgres_exporter` ready.
  - Full observability stack (self-hosted VMs) **deferred to Phase 3**.
- **Predict / actionable alerts?**
  - Cost guardrails (budget, >12h running), backup-verification, cert-renewal heartbeat.
  - Broader predictive alerting **deferred to Phase 3**.
- **Simulate failures?**
  - Staging env (`stg`) exists. Backlog: [failure simulation](../../backlog/failure-simulation.md).
- **Automation?**
  - Strong — Terraform, Helm/Helmfile, GitHub Actions for every op. No portal clicks.
- **Routine ops impact?**
  - AKS upgrades, cert renewal, backups. Backlog: [AKS upgrade runbook](../../backlog/aks-upgrade-runbook.md).
- **Learn from incidents?**
  - Pre-launch, none yet. Backlog: [incident-review process](../../backlog/incident-review-process.md).

**Decision: Split** — Adopt automation; Defer observability & incident learning to Phase 3.

### R5. Keep it simple

> Avoid overengineering the architecture, code, and operations.

- **Lean critical path?**
  - Yes — single region/cluster, single Postgres, nginx ingress (no AGW), no service mesh, no messaging. YAGNI throughout.
- **Standards + automated validation?**
  - Naming + tags (`workload`, `environment`, `managed_by`, `cost_center`, `owner`, `repo`); Terraform/Helm conventions; IaC validated in pipelines.
  - Azure Policy (policy-as-code) **out of scope** at this scale.
- **Pragmatic design?**
  - Yes — monolithic Flask, direct SQL, no premature decomposition.
- **Just enough code?**
  - Yes — single Python ETL CronJob, not Data Factory.
- **Platform features / prebuilt assets?**
  - Heavy reuse — managed AKS, CloudNativePG, cert-manager, nginx, CSI Secrets Store.

**Decision: Adopt**

---

## Security

Source: https://learn.microsoft.com/en-us/azure/well-architected/security/principles

### S1. Plan your security readiness

> Adopt security practices in design and operations with minimal friction.

- **Segmentation strategy?**
  - Per-environment isolation: separate clusters, Key Vaults, managed identities, WAL storage, Public IPs.
  - Namespaces + Cilium default-deny NetworkPolicy. Team: single owner.
- **Role-based training?**
  - N/A — solo operator.
- **Incident response plan?**
  - Backlog: [security incident response plan](../../backlog/security-incident-response.md).
- **Compliance requirements?**
  - None — public open data, personal project; no regulatory/industry standard applies.
- **Team-level security standards?**
  - No secrets in Git; GitHub Environments approval gate on prod; RBAC Key Vault + CSI Secrets Store; 30-day log retention.
- **SOC alignment?**
  - N/A — no SOC.

**Decision: Adapt** — right-sized for a solo/personal workload; formal IR plan deferred.

### S2. Design to protect confidentiality

> Prevent exposure of private/regulatory/proprietary information via access
> restrictions and obfuscation.

- **Strong / least-privilege access controls?**
  - Entra Workload Identity per pod-class; RBAC Key Vault; per-env identity scoping; IP-allowlisted API server; default-deny NetworkPolicy.
- **Data classification?**
  - App data = **public** (open data). Only **secrets** (DB credentials) are sensitive → Key Vault.
- **Encryption at rest / in transit / processing?**
  - At rest: default managed-key encryption + **encryption at host** on node pool.
  - In transit: cluster-internal TLS via cert-manager; Blob HTTPS enforced.
- **Guard against exploits?**
  - AKS kept on latest version. Image scanning deferred → [image vuln scanning](../../backlog/image-vulnerability-scanning.md).
- **Guard against exfiltration?**
  - Default-deny NetworkPolicy; no public Postgres endpoint; creds never in Git.
  - Egress via default AKS load balancer (Azure Firewall egress filtering out of scope — cost).
- **Confidentiality across flows?**
  - Internal TLS even for in-cluster traffic; secrets surfaced via CSI, not baked into images.
- **Audit trail?**
  - Container Insights logs (30-day). Formal audit logging out of scope (Phase 1).

**Decision: Adopt** (adapted) — strong for a demo; exploit-scanning + formal audit deferred.

### S3. Design to protect integrity

> Prevent corruption of design, implementation, operations, and data.

- **Authn/authz minimized by privilege/scope/time?**
  - Workload Identity + OIDC (no standing secrets); RBAC Key Vault; per-env scoping. No JIT/JEA (scoped-but-standing).
- **Supply-chain vulnerability protection?**
  - Backlog: [image vulnerability scanning](../../backlog/image-vulnerability-scanning.md) (Trivy in CI).
- **Cryptography for trust/verification?**
  - cert-manager TLS certs. Image signing (cosign) not planned at this scale.
- **Backup immutable + encrypted?**
  - Encrypted by default (GRS). Immutability → [backup immutability](../../backlog/backup-immutability.md).
- **Operating within intended limits?**
  - Pod resource requests/limits; NetworkPolicy constrains reachable surface.

**Decision: Adapt** — integrity basics (TLS, RBAC, no secrets in Git) adopted; supply-chain scanning + immutability deferred.

### S4. Design to protect availability

> Prevent/minimize downtime and degradation during a security incident.

- **Prevent compromised-identity misuse?**
  - Per-env identity scoping; least-privilege managed identities; no cross-env access. No JIT (scoped-standing accepted).
- **Prevent resource exhaustion (DDoS)?**
  - API server IP-allowlisted; pod resource limits. No WAF/Front Door (Phase 2, cost) — accepted given zero traffic + holding-page fallback.
- **Preventative measures (patches, scanners, malware)?**
  - AKS latest version/patching. Image scanning deferred (backlog). Antimalware N/A (managed nodes).
- **Prioritize controls on critical components?**
  - Postgres hardened: default-deny NetworkPolicy, no public endpoint, creds in Key Vault.
- **Same rigor in recovery resources?**
  - DR provisioned from same IaC/identities; GRS backups encrypted. Immutability pending (backlog).

**Decision: Adapt** — right-sized; DDoS/WAF deferred to Phase 2, accepted for now.

### S5. Sustain and evolve your security posture

> Continuous improvement and vigilance against evolving attackers.

- **Automated asset inventory?**
  - De-facto via Terraform state + resource tags. No dedicated inventory tool.
- **Threat modeling?**
  - Backlog: [threat model](../../backlog/threat-model.md).
- **Measure vs. baseline (posture management)?**
  - Microsoft Defender for Cloud secure score / Azure Policy **out of scope** (cost/complexity).
- **Periodic security tests + vuln scanning?**
  - No pen testing. Vuln scanning deferred → [image vuln scanning](../../backlog/image-vulnerability-scanning.md).
- **Detect/respond/recover?**
  - Container Insights only; no SIEM. Limited by design.
- **Post-incident activities?**
  - Backlog: [incident-review process](../../backlog/incident-review-process.md).
- **Get / stay current?**
  - AKS kept on latest version; dependency updates via GitHub.

**Decision: Defer** (mostly) — posture management, threat modeling, pen testing, vuln scanning deferred; patching adopted. Weakest security area by design.

---

## Cost Optimization

Source: https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/principles

### C1. Develop cost-management discipline

> Build awareness of budget, expenses, reporting, and cost tracking.

- **Cost model?**
  - Per-resource cost estimates in the technology-choices analysis; TCO segmented (compute, storage, identities, DR).
- **Accountability model?**
  - Solo owner; tags include `cost_center` + `owner`.
- **Realistic budgets + thresholds?**
  - **$100/mo hard cap**, alerts at 50%/80%, steady-state $25–50. In [spec.md](../../../ref/spec.md).
- **SLA penalties vs. implementation?**
  - N/A — no SLA.
- **Training/hiring/infra costs?**
  - Minimal — solo operator, free/open-source tooling.
- **Communicate cost implications of changes?**
  - Decision log in the AKS planning doc (e.g., passive-cold DR chosen with $/mo rationale).

**Decision: Adopt.**

### C2. Design with a cost-efficiency mindset

> Spend only on what you need for the highest ROI.

- **Cost baseline fits budget?**
  - Steady-state $25–50 within the $100 cap; every technology choice is cost-justified.
- **Cost guardrails?**
  - Budget alerts + **auto-shutdown at 100%**; alert if a cluster runs >12h; **clusters stopped by default**.
- **SDLC environments differently?**
  - Prod + staging both stopped by default and started on demand; no always-on non-prod cost.

**Decision: Adopt.**

### C3. Design for usage optimization

> Maximize use of resources and operations against negotiated requirements.

- **Full capabilities of SKUs?**
  - AKS Free control-plane tier; B2s burstable VMs (use burst credits, not idle capacity).
- **Dynamically adjust capacity?**
  - Cluster autoscaler (`syspool` 1–2, `usrpool` 1–3); stop-by-default is the biggest lever.
- **Active-active over active-passive?**
  - No — passive-cold DR chosen deliberately; we do **not** pay for a standing secondary, so there are no idle paid resources to convert.
- **Commitment-based discounts?**
  - No — spot VMs instead; reservations don't fit bursty, stop-by-default usage.
- **Support plan?**
  - N/A — no paid support plan (community/free).

**Decision: Adopt** (adapted) — usage optimized via stop-by-default, autoscale, and spot; reservations/active-active deliberately unused.

> **Reviewer note:** WAF's cost pillar recommends reservations and active-active
> for already-paid resources. Both were **evaluated and consciously rejected**
> here — stop-by-default leaves near-zero idle compute, so reservations would be
> wasteful and there is no idle paid capacity to convert to active-active.

### C4. Design for rate optimization

> Increase efficiency without redesigning or sacrificing requirements.

- **Reservations for stable usage?**
  - No — bursty, stopped-by-default usage; reservations would waste money. Spot chosen instead.
- **No-additional-licensing alternatives?**
  - Yes — open-source throughout (PostgreSQL, Grafana, nginx, cert-manager, CloudNativePG); zero licensing.
- **Consumption-based pricing?**
  - Yes — pay-as-you-go compute, billed near-zero while stopped. The core cost lever.
- **Fixed-price billing?**
  - No — low/unpredictable utilization makes consumption cheaper.
- **Co-locate usage?**
  - Yes — Flask, Grafana, ETL, and Postgres share one cluster/node pool (compute consolidation).
- **Lower-cost regions?**
  - Cheapest North America region chosen at implementation (see [spec.md](../../../ref/spec.md)).
- **Higher density?**
  - Yes — one cluster hosts all workloads; security boundary held by NetworkPolicy.

**Decision: Adopt.**

### C5. Monitor and optimize over time

> Continuously right-size investment as the workload evolves.

- **Capture/classify expense?**
  - Resource tags (`workload`, `environment`, `managed_by`, `cost_center`, `owner`, `repo`) enable breakdown in Azure Cost Management.
- **Cost alerts at thresholds?**
  - 50%/80% warnings, 100% auto-shutdown. Review cadence → [cost alert review cadence](../../backlog/cost-alert-review-cadence.md).
- **Continuously evaluate/adjust?**
  - Decision log; planned tier upgrade (Standard HDD → SSD, Q1 2028) shows ongoing review.
- **Decommission underutilized/obsolete?**
  - Stop-by-default is continuous decommission; ACR untagged-image cleanup workflow; delete unnecessary data.

**Decision: Adopt.**

---

## Operational Excellence

Source: https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/principles

### O1. Embrace DevOps culture

> Continuously improve system design and processes through collaboration,
> shared responsibility, and ownership.

- **Common systems/tools + shared backlog?**
  - Single Git repo; GitHub Issues + Actions. Escalation paths N/A (solo).
- **Continuous learning / blameless postmortems?**
  - Documentation set (this planning) + session journals; postmortems → [incident-review process](../../backlog/incident-review-process.md).
- **Agile practices + shift-left?**
  - Lightweight; shift-left via CI checks in pipelines.
- **Standards for dev/ops procedures + drills?**
  - Runbook catalog (RB-01..RB-16); emergency drill → [recovery drill](../../backlog/recovery-drill.md).
- **Centralized ops teams?**
  - No — solo operator.

**Decision: Adapt** — DevOps practices at solo scale; team/centralized aspects N/A.

### O2. Establish development standards

> Standardize development practices, enforce quality gates, and track progress.

- **Document features + derive requirements + sizing?**
  - Planning docs + [spec.md](../../../ref/spec.md); sizing = pod resource requests.
- **Methodology + shared backlog?**
  - Lightweight; GitHub Issues. No formal Scrum (solo).
- **Source control strategy?**
  - Git; feature branches + PR workflow (audit trail). Peer review N/A (solo).
- **QA / early testing / immutable artifacts?**
  - Immutable container images promoted across envs; CI checks. Synthetic e2e tests deferred to Phase 2.
- **Style guides / conventions?**
  - Repo conventions + `CLAUDE.md` doc/code standards; Terraform/Helm style.
- **Code docs as written?**
  - Doc-as-you-go + session journals (per `CLAUDE.md`).
- **Progress/trend reporting?**
  - Minimal — solo; not formalized.

**Decision: Adapt** — standards at solo scale; formal QA/trend reporting kept light.

### O3. Evolve operations with observability

> Gain visibility, derive insight, make data-driven decisions.

- **Decoupled monitoring stack?**
  - Phase 1: Container Insights + Azure Monitor. Full stack (Prometheus/Grafana on self-hosted VMs) → Phase 3.
- **Standardize collection per source?**
  - `postgres_exporter` sidecar; Container Insights for cluster/app logs.
- **Emit correlated telemetry from app?**
  - Flask `/health` today; broader instrumentation → Phase 3.
- **Own emitting/collecting when shared?**
  - Shared Log Analytics workspace, owned by the workload.
- **Just enough data / retention?**
  - 30-day retention (cost tradeoff).
- **Distinguish signals?**
  - Metrics (exporter) + logs (Container Insights); distributed **tracing** deferred to Phase 2.
- **Aggregate/visualize dashboards?**
  - Grafana (app) + Azure Monitor; operator dashboards → Phase 3.
- **Actionable alerts?**
  - Cost, backup-verify, cert-renewal, >12h-cluster alerts (action-only).

**Decision: Split** — Phase 1 baseline adopted; full observability + tracing deferred to Phase 2/3 (ties to R4).

### O4. Automate for efficiency

> Replace repetitive manual tasks with software automation.

- **Evaluate + prioritize workflows?**
  - GitHub Actions for cluster lifecycle, app deploy, DR, secret rotation, dataset refresh, monitoring deploy.
- **Build vs. buy?**
  - Buy the platform (GitHub Actions); build custom workflows for specialized ops.
- **Components designed for automation?**
  - IaC (Terraform) + Helm + parameterized `workflow_dispatch`.
- **Automation as critical dependency (5 pillars)?**
  - OIDC-secured workflows, per-env identity scoping.
- **Automate at scale ("design once, run everywhere")?**
  - Environment-parameterized workflows (no per-env wrappers); identical Terraform module for prod + DR.

**Decision: Adopt** — a core strength.

### O5. Adopt safe deployment practices

> Use guardrails that reduce the effect of errors and unexpected conditions.

- **IaC for desired state?**
  - Terraform per env + Helm/Helmfile; remote state in Azure Blob with blob-lease locking.
- **Small, incremental, frequent updates?**
  - Small releases via feature-branch workflow.
- **Automated pipelines across envs?**
  - GitHub Actions for all deploys; GitHub Environments approval gate on prod.
- **Test updates rigorously?**
  - Staging environment (`stg`); synthetic e2e tests deferred to Phase 2.
- **Progressive-exposure rollout?**
  - Minimal by scale — single-instance, no canary/blue-green. Per-PR preview envs → Phase 2.
- **Compensating/rollback + emergency process?**
  - Helm rollback + IaC reprovision; DR runbook (RB-16, backlog). Pre-approved emergency path is informal.

**Decision: Adopt** (adapted) — IaC + pipelines + approval gate adopted; progressive rollout minimal by scale.

---

## Performance Efficiency

Source: https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/principles

### P1. Negotiate realistic performance targets

> Define the intended user experience and a strategy to benchmark and measure
> against business requirements.

- **Prepare to set targets?**
  - Small static dataset (~100k rows); informal target is sub-second query. No production history yet.
- **User expectations / standards?**
  - Loose by design — "fast enough" page loads; no latency SLA/SLO.
- **Critical flows + tolerance ranges?**
  - Flows A/B critical, but tolerances not quantified. Connection target still _TBD_ in [spec.md](../../../ref/spec.md).
- **Performance model?**
  - None formal — deferred; no traffic to model yet.

**Decision: Adapt** — targets intentionally loose; formal model deferred.

### P2. Design to meet capacity requirements

> Provide enough supply to address anticipated demand.

- **Dynamic scaling needs per flow?**
  - Low — cluster autoscaler + burstable VMs suffice. HPA deferred to Phase 2.
- **Right-sized + autoscale features?**
  - B2s burstable; Postgres requests (250m CPU / 512Mi in prod); Standard SSD (E10); cluster autoscaler.
- **Capacity planning / predictive modeling?**
  - None — vertical scaling (larger node) if ever needed.
- **Proof of concept?**
  - The existing dockerized deployment is the working PoC.

**Decision: Adapt** — right-sized for a small dataset; HPA/predictive modeling deferred.

### P3. Achieve and sustain performance

> Protect against performance degradation while the system is in use and evolves.

- **Performance testing strategy?**
  - None in Phase 1; load testing (k6) deferred to Phase 2.
- **Perf tests as quality gates?**
  - No — deferred with the load-test tooling.
- **Performance monitoring + regression alerts?**
  - Baseline metrics via Container Insights / `postgres_exporter`; formal perf monitoring → Phase 3.
- **Review data as usage grows?**
  - Deferred — no usage yet.
- **Design patterns to fine-tune (caching/pooling)?**
  - PgBouncer pooling → Phase 2; read replicas → Phase 3; Redis cache considered, not needed.
- **Performance-focused coding standards?**
  - Minimal — small app, direct SQL.

**Decision: Defer** — sustaining practices deferred to Phase 2/3; no traffic to justify them now.

### P4. Optimize for long-term improvement

> Improve system efficiency within defined targets to increase workload value.

- **Dedicated time for perf optimization?**
  - No regular cadence — ad-hoc, revisited if usage appears.
- **Revisit NFRs from production trends?**
  - Deferred until real usage data exists (e.g., planned Standard HDD → SSD upgrade, Q1 2028).
- **Stay current with updates?**
  - AKS kept on latest version; dependency/library updates via GitHub.

**Decision: Defer** — revisit with production data; staying current is adopted.
