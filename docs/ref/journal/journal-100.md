# Journal 100

## 2026-06-19 — Complete "Data Model" section in arch-design-planning.md

### Context

The `### Data Model` subsection under "Choose a data store" was a stub
containing only the MS Learn URL with no explanatory content.

User asked to read the article and write a 1-paragraph explanation of what
data model best applies to DineSafeViz.

### Work log

#### 2026-06-19 — Fetched MS Learn article

URL: https://learn.microsoft.com/en-us/azure/architecture/data-guide/technology-choices/understand-data-store-models

Key takeaways:
- Article classifies nine storage models: relational, document, column-family,
  key-value, graph, time-series, object, search, and vector.
- Heuristic table maps "strict multi-entity transactions" and "complex joins"
  to the relational model.
- Relational strengths: multi-row transactional consistency, complex joins,
  strong constraints, mature tooling.
- Other models all fail DineSafeViz's access pattern: no NoSQL schema
  flexibility needed, no high-ingest stream, no graph traversal, no full-text
  search, not an analytics MPP workload.

### Decision

DineSafeViz is a clear relational (OLTP) workload. The paragraph explains the
taxonomy, maps DineSafeViz's access patterns to the heuristic table, and
eliminates the other models in one concise pass.

### Files edited

- `docs/ref/arch/arch-design-planning.md`: replaced URL stub in
  `### Data Model` with a 1-paragraph explanation.

---

## 2026-06-19 — Complete "Prepare to choose a data store in Azure" section

### Context

The section had stub content — article criteria pasted verbatim with no
DineSafeViz-specific answers. Key questions were listed but unanswered.

User asked to read the MS Learn article and fill in answers, with explicit note:
although MySQL would be sufficient, PostgreSQL is chosen to demonstrate
enterprise-grade DB administration. MS SQL excluded on cost.

### Work log

URL fetched: https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/data-stores-getting-started

Subsections filled in:
- Functional requirements (11 criteria)
- Nonfunctional requirements (4 criteria)
- Cost and management considerations (4 criteria, including PG vs MySQL vs
  MS SQL rationale)
- Security and governance (4 criteria)
- DevOps and team readiness (3 criteria)
- Key questions (10 questions answered inline)

Key decisions captured:
- PostgreSQL over MySQL: both technically sufficient; PostgreSQL chosen for
  enterprise-grade portfolio demonstration value.
- MS SQL excluded: no perpetual free tier; licensing overhead unjustified.
- Self-hosted over PaaS: cost delta ~$15/mo; removes operational showcase.

---

## 2026-06-19 — Complete "OLTP Solutions" section

### Context

`#### OLTP Solutions` was a stub: the Azure service list and key selection
criteria were copied verbatim from the MS Learn article with no DineSafeViz
answers.

### Work log

URL fetched: https://learn.microsoft.com/en-us/azure/architecture/data-guide/relational-data/online-transaction-processing

Added:
- Intro paragraph noting DineSafeViz isn't a classic business-transaction
  system but matches the OLTP trait profile.
- `##### Workload trait fit` table mapping each of the 13 OLTP traits to
  DineSafeViz's actual characteristics.
- `##### Key selection criteria` — moved service list inline, answered all 9
  key questions as a sequential elimination funnel leading to self-hosted
  PostgreSQL.

---

## 2026-06-19 — Complete "Design Pattern" section in design-planning/Readme.md

### Context

The `## Design Pattern` section in `docs/ref/arch/design-planning/Readme.md`
was blank. User asked to evaluate all 15 patterns from the MS Learn
operational excellence design patterns article and identify which apply to
deploying DineSafeViz on AKS.

### Work log

URL fetched: https://learn.microsoft.com/en-us/azure/well-architected/operational-excellence/design-patterns

Evaluated all 15 patterns. 7 applicable, 8 not applicable.

Applicable:
- Compute Resource Consolidation: shared AKS node pool for all workloads
- Deployment Stamps: versioned Helm + Terraform; DR cold cluster is a stamp
- External Configuration Store: ConfigMaps + Key Vault CSI driver
- Gateway Offloading: nginx ingress TLS termination
- Gateway Routing: nginx ingress path routing Flask/Grafana
- Health Endpoint Monitoring: AKS liveness/readiness probes + /health endpoint
- Sidecar: postgres_exporter sidecar for metrics

Not applicable: Anti-Corruption Layer, Strangler Fig (no legacy), Choreography,
Publisher/Subscriber, Messaging Bridge (no event bus), Gateway Aggregation
(no multi-backend clients), Edge Workload Configuration (not edge), Quarantine
(weak fit for v0.4 — flagged for future revisit).

Notable: Gateway Offloading + Gateway Routing both satisfied by a single nginx
ingress controller — highlighted in the table and noted for reviewers.
