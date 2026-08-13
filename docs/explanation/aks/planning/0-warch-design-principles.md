# 0. Well-Architected Design Principles

Step 1 of the [WAF suggested learning process](https://learn.microsoft.com/en-us/azure/well-architected/what-is-well-architected-framework#suggested-learning-process):
**understand all of the design principles and craft a design strategy.**

All five pillars apply to this workload. Every design principle below must be
considered — none are optional. For each principle, record a **decision**:

- **Adopt** — implement the approach as recommended.
- **Adapt** — implement a lighter/modified version (state how).
- **Defer** — valid but postponed to a later phase (state which).
- **N/A** — not applicable to this workload (state why).

The questions under each principle are derived from the "Approach" rows of the
Microsoft principle articles. They are the prompts we must answer to justify
each decision against DineSafeViz's requirements and budget.

> Status: **in progress.** Reliability + Security answered; Cost, Operational
> Excellence, and Performance Efficiency pending.

## Summary

High-level decision per design principle. Details in the pillar sections below.

| Pillar | ID | Design principle | Decision |
|---|---|---|---|
| Reliability | R1 | Design for business requirements | Adopt |
| Reliability | R2 | Design for resilience | Adapt |
| Reliability | R3 | Design for recovery | Adopt |
| Reliability | R4 | Design for operations | Split (adopt automation / defer observability) |
| Reliability | R5 | Keep it simple | Adopt |
| Security | S1 | Plan your security readiness | Adapt |
| Security | S2 | Design to protect confidentiality | Adopt |
| Security | S3 | Design to protect integrity | Adapt |
| Security | S4 | Design to protect availability | Adapt |
| Security | S5 | Sustain and evolve your security posture | Defer (mostly) |
| Cost Optimization | C1 | Develop cost-management discipline | _TBD_ |
| Cost Optimization | C2 | Design with a cost-efficiency mindset | _TBD_ |
| Cost Optimization | C3 | Design for usage optimization | _TBD_ |
| Cost Optimization | C4 | Design for rate optimization | _TBD_ |
| Cost Optimization | C5 | Monitor and optimize over time | _TBD_ |
| Operational Excellence | O1 | Embrace DevOps culture | _TBD_ |
| Operational Excellence | O2 | Establish development standards | _TBD_ |
| Operational Excellence | O3 | Evolve operations with observability | _TBD_ |
| Operational Excellence | O4 | Automate for efficiency | _TBD_ |
| Operational Excellence | O5 | Adopt safe deployment practices | _TBD_ |
| Performance Efficiency | P1 | Negotiate realistic performance targets | _TBD_ |
| Performance Efficiency | P2 | Design to meet capacity requirements | _TBD_ |
| Performance Efficiency | P3 | Achieve and sustain performance | _TBD_ |
| Performance Efficiency | P4 | Optimize for long-term improvement | _TBD_ |

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

**Decision: Adopt** — a relative strength.

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

**Decision: Adopt** — a core design driver.

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

Questions & decisions:

1. What is our **cost model** (segment expenses; estimate/forecast total cost
   of ownership)?
2. What is the **accountability model** (roles, responsibilities, governance)?
3. What are the **realistic budgets** covering requirements, personnel,
   processes, and anticipated growth, with threshold notifications?
4. For any SLA, do we budget toward **penalties vs. implementation**? (Likely
   N/A — no SLA.)
5. What **training/hiring/infra costs** accompany workload maturity?
6. How do we **communicate cost implications** of design changes learned from
   production?

**Decision:** _TBD_

### C2. Design with a cost-efficiency mindset

> Spend only on what you need for the highest ROI.

Questions & decisions:

1. What is our **cost baseline** (including projected growth) and do design
   choices fit the budget?
2. What **cost guardrails** keep resources within upper/lower limits?
3. How do we **treat SDLC environments differently** (prod vs. non-prod SKUs,
   counts, logging; on-demand teardown)?

**Decision:** _TBD_

### C3. Design for usage optimization

> Maximize use of resources and operations against negotiated requirements.

Questions & decisions:

1. Are we using the **full capabilities of selected SKUs** (not paying for
   unused features)?
2. Where do we **dynamically adjust capacity** (scale up/down with demand)?
3. Do we prefer **active-active over active-passive** where resources are
   already paid for?
4. Do we use **commitment-based discounted resources** for new work?
5. Are we making the most of any **support plan** and training allowance?

**Decision:** _TBD_

### C4. Design for rate optimization

> Increase efficiency without redesigning or sacrificing requirements.

Questions & decisions:

1. Which resources have **stable/predictable usage** suitable for prepurchase
   discounts (reservations)?
2. Are there **no-additional-licensing alternatives** (hybrid use, pre-prod
   pricing)?
3. Where is **consumption-based pricing** more cost-effective?
4. Where is **fixed-price billing** better (high, predictable utilization)?
5. Can we **co-locate usage** with other workloads/teams to share cost?
6. Can we deploy to **lower-cost regions** (esp. non-prod) without compromise?
7. Where do we prefer services that enable **higher density** (mind security
   boundaries)?

**Decision:** _TBD_

### C5. Monitor and optimize over time

> Continuously right-size investment as the workload evolves.

Questions & decisions:

1. What captures and **classifies expense** (showback/chargeback boundaries)?
2. What **cost alerts** fire at budget thresholds, and how are they reviewed?
3. How do we **continuously evaluate/adjust** design decisions on cost?
4. How do we **decommission underutilized/obsolete resources** and delete
   unnecessary data?

**Decision:** _TBD_

---

## Operational Excellence

Source: https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/principles

### O1. Embrace DevOps culture

> Continuously improve system design and processes through collaboration,
> shared responsibility, and ownership.

Questions & decisions:

1. What **common systems and tools** promote collaboration and progress
   tracking (shared backlog, escalation paths)?
2. How do we build a **continuous learning/experimentation mindset** (blameless
   postmortems, knowledge sharing, docs)?
3. What **agile practices** and **shift-left** opportunities do we adopt?
4. What **standards for development and operational procedures** do we set and
   review on a cadence (incl. emergency drills)?
5. Do we use any **centralized operations teams** / shared resources? (Likely
   solo — state so.)

**Decision:** _TBD_

### O2. Establish development standards

> Standardize development practices, enforce quality gates, and track progress.

Questions & decisions:

1. How do we **document workload features** and derive functional/nonfunctional
   requirements and sizing estimates?
2. What **software development methodology** and shared backlog do we use for
   our team size?
3. What **source control** strategy (branching, peer review, audit trail)
   covers code, scripts, templates, pipelines, docs?
4. What **quality assurance** / early testing and immutable-artifact promotion
   through quality gates do we use?
5. What **style guides, tooling, and conventions** (patterns, API design,
   logging, exception handling) enforce consistency?
6. How do we insist on **code documentation as it's written**?
7. What **progress/trend reporting** (bugs, failed updates, time-to-deploy)
   measures efficiency?

**Decision:** _TBD_

### O3. Evolve operations with observability

> Gain visibility, derive insight, make data-driven decisions.

Questions & decisions:

1. Do we build a **decoupled monitoring stack** covering infra, app health, and
   build/release?
2. How do we **standardize collection** per data-source type (telemetry
   standards, instrumentation)?
3. How does app code **emit correlated telemetry** across the execution flow?
4. Who **owns emitting/collecting data** even when sinks are shared/central?
5. Do we collect **just enough data for just enough time** (cost tradeoffs)?
6. Do we distinguish the **monitoring signals** (profiles, logs, metrics,
   traces) and use each for its right purpose?
7. How do we **aggregate/visualize in dashboards** (situational vs.
   operational)?
8. How do we make **alerts actionable** (accountable roles, severity, proactive
   thresholds, action-only triggers)?

**Decision:** _TBD_

### O4. Automate for efficiency

> Replace repetitive manual tasks with software automation.

Questions & decisions:

1. How do we **evaluate workflows** (complexity, effort, frequency, accuracy,
   lifespan) and prioritize which to automate/remove?
2. For each automation, do we **build vs. buy** (explicit decision)?
3. Are workload components **designed to support automation**?
4. Do we treat **automation as a critical dependency** that adheres to all five
   pillars?
5. Where do we **automate at scale** ("design once, run everywhere" templates)?

**Decision:** _TBD_

### O5. Adopt safe deployment practices

> Use guardrails that reduce the effect of errors and unexpected conditions.

Questions & decisions:

1. How do we use **IaC** for desired state (modular, layered, lifecycle-
   aligned)?
2. Do we prefer **small, incremental, frequent updates**?
3. Are all code and infra changes deployed via **automated pipelines** across
   environments?
4. How do we **test updates rigorously** in pre-prod and prod?
5. What **progressive-exposure rollout patterns** (with backward/forward
   compatibility) do we use? (May be minimal at this scale — state so.)
6. What **compensating/rollback actions** and pre-approved emergency process
   recover from faulty deployments?

**Decision:** _TBD_

---

## Performance Efficiency

Source: https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/principles

### P1. Negotiate realistic performance targets

> Define the intended user experience and a strategy to benchmark and measure
> against business requirements.

Questions & decisions:

1. How do we **prepare to set targets** (technical options, historical data,
   usage patterns, bottlenecks, industry standards)?
2. What **user expectations / performance standards** do we align on given
   investment level?
3. Which **critical flows** get prioritized, with performance tolerance ranges
   (ideal → unacceptable)?
4. What **performance model** (usage patterns, business impact, operational
   cost) yields initial targets, refined iteratively?

**Decision:** _TBD_

### P2. Design to meet capacity requirements

> Provide enough supply to address anticipated demand.

Questions & decisions:

1. What are the **dynamic scaling needs** per prioritized flow (elasticity)?
2. Are resources **right-sized** across the stack, using built-in autoscale
   features?
3. What **capacity planning / predictive modeling** forecasts future capacity?
4. Do we validate design choices with a **proof of concept**?

**Decision:** _TBD_

### P3. Achieve and sustain performance

> Protect against performance degradation while the system is in use and evolves.

Questions & decisions:

1. What is our **performance testing strategy** (manual + pipeline-integrated
   tests)?
2. Are performance tests **quality gates**?
3. What **performance monitoring** (end-to-end transactions + technical metrics,
   real + synthetic) and regression alerts do we set?
4. How do we **review test/monitoring data** as usage grows and backlog
   remediation?
5. What **design patterns** fine-tune performance across app/compute/data
   layers?
6. What **performance-focused coding standards** do we follow?

**Decision:** _TBD_

### P4. Optimize for long-term improvement

> Improve system efficiency within defined targets to increase workload value.

Questions & decisions:

1. Do we set aside **dedicated time for performance optimization** as regular
   practice?
2. Do we **revisit nonfunctional requirements** and set new targets from
   production trends (caching, CDN, etc.)?
3. How do we **stay current** with framework/library/platform updates that
   affect performance?

**Decision:** _TBD_
