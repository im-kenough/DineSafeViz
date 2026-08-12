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

> Status: **template only.** Questions listed; answers to be filled in a later
> pass.

---

## Reliability

Source: https://learn.microsoft.com/en-us/azure/well-architected/reliability/principles

### R1. Design for business requirements

> Get clarity on the workload's scope, user growth, and the promises made to
> external customers and internal stakeholders.

Questions & decisions:

1. What level of resiliency, recovery, observability, and simplicity is
   required? What is "good enough"?
2. Are there defined constraints related to cost, compliance, geography, or
   latency?
3. What are the architectural trade-offs (financial cost, engineering
   complexity, security, operational overhead) we are presenting and accepting?
4. What are the reliability outcomes for each **critical user flow** (not just
   generic uptime)? What is each flow's business value, usage pattern, and
   resilience requirement?
5. What are the time-horizon usage expectations — user load at launch, and is
   growth linear, exponential, or uncertain?
6. What external dependencies limit our autonomy (org constraints, centralized
   infra, security mandates, network policy, platform decisions), and how do
   they affect achievable RTO/RPO/SLO?

**Decision:** _TBD_

### R2. Design for resilience

> The workload must continue to operate with full or reduced functionality.

Questions & decisions:

1. Which components are on the **critical path** vs. able to run in a degraded
   state?
2. What are the potential **failure points** for critical components, and the
   effect (full vs. partial outage) on user flows?
3. What **self-preservation** capabilities (design patterns, modularization,
   fault isolation) do we build in?
4. How do critical components **scale out**, given regional capacity
   constraints?
5. Where do we build **redundancy in layers** (physical, data replication,
   functional/services/personnel) — active-active or active-passive?
6. Do we **overprovision** to absorb individual failures and runaway resource
   consumption? By how much?

**Decision:** _TBD_

### R3. Design for recovery

> The workload must anticipate and recover from failures of all magnitudes with
> minimal disruption.

Questions & decisions:

1. Do we have structured, tested, documented **recovery plans** aligned to
   negotiated recovery targets (per component and system-wide)? Are recovery
   drills scheduled?
2. Can we **repair data** for all stateful components within recovery targets
   (immutable, transactionally consistent backups)?
3. What **automated self-healing** capabilities are in the design?
4. Which stateless components are replaced with **immutable ephemeral units**
   (side-by-side / repeatable deployment)?

**Decision:** _TBD_

### R4. Design for operations

> Shift left in operations to anticipate failure conditions.

Questions & decisions:

1. How do we build **observable systems** that correlate telemetry (component
   and end-to-end user-flow level)?
2. How do we **predict malfunctions** and surface prioritized, actionable
   alerts?
3. Do we **simulate failures** / test in pre-production and production?
4. What is built with **automation in mind**, and how much is automated?
5. How do **routine operations** (revisions, audits, upgrades, backups) affect
   system stability, and how do we scrutinize them?
6. How do we **learn from production incidents** and drive improvements?

**Decision:** _TBD_

### R5. Keep it simple

> Avoid overengineering the architecture, code, and operations.

Questions & decisions:

1. Is every component justified by target business value? Is the **critical
   path lean**?
2. What **standards** (naming, code style, deployment, process) do we establish
   and enforce with automated validation?
3. Do our approaches translate to **pragmatic design** for our use cases (not
   over-granular)?
4. Are we developing **just enough code**?
5. Where do we **use platform-provided features** and prebuilt assets instead
   of building our own?

**Decision:** _TBD_

---

## Security

Source: https://learn.microsoft.com/en-us/azure/well-architected/security/principles

### S1. Plan your security readiness

> Adopt security practices in design and operations with minimal friction.

Questions & decisions:

1. What is our **segmentation strategy** (environment, processes, team) to
   isolate access and function?
2. What **role-based security skills/training** do we need?
3. Do we have an **incident response plan** (preparedness, detection,
   containment, mitigation, post-incident)?
4. What external **security compliance requirements** (org policy, regulatory,
   industry standards) apply?
5. What **team-level security standards** (coding, gated approvals, release
   management, data protection/retention) do we define and enforce?
6. How does incident response align with any centralized **SOC** function?

**Decision:** _TBD_

### S2. Design to protect confidentiality

> Prevent exposure of private/regulatory/proprietary information via access
> restrictions and obfuscation.

Questions & decisions:

1. What **strong access controls** grant access on a need-to-know / least-
   privilege basis?
2. How is data **classified** by type, sensitivity, and risk, with a
   confidentiality level per class?
3. What **encryption** at rest, in transit, and in processing do we apply per
   confidentiality level?
4. How do we **guard against exploits** that expose information (auth,
   configuration, code, operations)?
5. How do we **guard against data exfiltration** (networking, identity,
   encryption controls)?
6. How do we **maintain confidentiality as data flows** across components /
   security tiers?
7. What **audit trail** of access activities do we keep?

**Decision:** _TBD_

### S3. Design to protect integrity

> Prevent corruption of design, implementation, operations, and data.

Questions & decisions:

1. What **access controls** authenticate/authorize and minimize access by
   privilege, scope, and time?
2. How do we protect and detect vulnerabilities in the **supply chain**
   (build-time and runtime scanning)?
3. What **cryptography** (attestation, code signing, certificates, encryption)
   establishes trust and verification?
4. Is **backup data immutable and encrypted** when replicated/transferred?
5. How do we prevent the workload from **operating outside its intended limits
   and purpose**?

**Decision:** _TBD_

### S4. Design to protect availability

> Prevent/minimize downtime and degradation during a security incident.

Questions & decisions:

1. How do we prevent **compromised identities** from misusing access (scope /
   time limits, JIT/JEA)?
2. What controls/patterns prevent **resource exhaustion** attacks (e.g. DDoS)?
3. What **preventative measures** address attack vectors in code, network
   protocols, identity, and malware?
4. How do we **prioritize security controls** on critical components and flows?
5. Do **recovery resources and processes** get the same security rigor as
   production?

**Decision:** _TBD_

### S5. Sustain and evolve your security posture

> Continuous improvement and vigilance against evolving attackers.

Questions & decisions:

1. Do we maintain an automated **asset inventory** (resources, locations,
   dependencies, owners, metadata)?
2. Do we perform **threat modeling** to identify and prioritize threats?
3. How do we **measure current state** against a security baseline and set
   remediation priorities (posture management, compliance enforcement)?
4. Do we run **periodic security tests** (pen testing) and integrated
   **vulnerability scanning**?
5. How do we **detect, respond, and recover** with swift security operations?
6. Do we run **post-incident activities** (root-cause, postmortems, reports)?
7. How do we **get current and stay current** (patching, SDL reviews, threat
   intelligence, automation)?

**Decision:** _TBD_

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
