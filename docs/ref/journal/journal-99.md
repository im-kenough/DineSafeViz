# Journal 99

## 2026-06-18 — Rewrite "Choose a data store" section in arch-design-planning.md

### Context

The existing `### Choose a data store` section selects Azure Database for
PostgreSQL — Flexible Server as the managed target. User asked to redo the
section after reading two MS Learn articles, with three explicit questions:

1. Is managed Azure Database for PostgreSQL overkill for DineSafeViz?
2. Cost comparison vs running PostgreSQL in a container in AKS.
3. Best practices.

User also surfaced a forward-looking backup and DR plan:
- 00:30 ETL CronJob pulls new DineSafe data.
- 02:00 nightly DB snapshot.
- GitHub Actions replicates snapshot to a DR region.
- Active-passive failover: cold AKS in DR region, DNS cutover on failover.

### Analysis

- For ~100k rows, single-region, read-mostly demo workload, managed PG is
  cost-disproportionate (~$16–20/mo list vs ~$2–3/mo self-hosted; no permanent
  free tier).
- Managed PG hides the operational surface (backups, snapshots, replication,
  failover) that the portfolio is meant to demonstrate.
- The DR plan as described maps cleanly onto self-hosted PG with CloudNativePG
  (WAL archiving + scheduled base backups in Blob, replicated via GH Actions).

### Direction confirmed with user

- Self-hosted PG in AKS as selected option.
- CloudNativePG operator (CNCF Sandbox) as the deployment pattern.

### Work log

#### 2026-06-18 — Fetched MS Learn docs

- https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/technology-choices-overview
- https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/data-stores-getting-started

Key callouts pulled from `data-stores-getting-started`:
- Functional/non-functional/cost/security/devops requirement taxonomy.
- "Licensing and portability: Vendor lock-in and open-source compatibility"
  explicitly listed as a cost/management consideration — supports the
  self-hosted PG portability narrative.
- PaaS vs IaaS framed as control vs operational overhead, not as a directive.

#### 2026-06-18 — Rewrote section

Edited `docs/ref/arch/arch-design-planning.md`:

- Rewrote intro paragraph: managed PG → self-hosted PG on AKS via CloudNativePG.
- Rewrote decision tree path; question 5 (PaaS/IaaS) now answers self-hosted
  IaaS/containerized, with the rationale deferred to the cost subsection.
- Added new "Is managed Azure Database for PostgreSQL overkill?" subsection
  with cost comparison table and portfolio rationale.
- Added new "Best practices for self-hosted PostgreSQL on AKS" subsection with
  CloudNativePG configuration practices table.
- Added new "Backup and disaster recovery roadmap" subsection with daily cycle,
  DR-region steady state, and failover runbook.
- Updated the candidates evaluated table: added self-hosted variants (CNPG
  selected, Bitnami and Zalando/Crunchy rejected); demoted Azure Database for
  PostgreSQL — Flexible Server to rejected with cost + portfolio reasoning.
- Preserved the existing "Notes on tangential sub-articles" subsection
  (data lake, pipeline orchestration, search) unchanged.

Updated the Technology Choices Summary block: added a `Data Store` entry
listing self-hosted PostgreSQL on AKS with the CloudNativePG operator.

#### 2026-06-18 — Added scheduled jobs / DR runbook planning notes to arch-dr.md

User followed up asking about best practices for scheduled jobs (00:30 ETL,
02:00 snapshot, 02:15 cross-region replication, DR cutover) — specifically
whether they all belong in GitHub Actions.

Answered conversationally first with the placement principle: in-cluster
dependencies → Kubernetes; Azure resource movement → GitHub Actions; DR
cutover → GitHub Actions specifically because the primary region may be
down. User then asked to capture this in `docs/ref/arch/arch-dr.md`.

Edited `docs/ref/arch/arch-dr.md`:

- Preserved the two existing scenario stubs (City Open Data unavailable,
  AKS backup and recovery — both still TODO).
- Appended a new `## Scheduled jobs and DR runbooks` section with:
  - Guiding principle on runtime selection.
  - Per-job placement table (ETL, DB backup via CloudNativePG
    `ScheduledBackup`, cross-region replication, DR cutover).
  - Cross-cutting best practices (one identity story per surface,
    idempotency, explicit time zones, failure surfacing, cutover
    guardrails, no DR dependency on the failed region).
  - "Why not run everything in GitHub Actions" subsection covering network
    reach, free-tier minute limits, and GitHub-uptime coupling.

Flagged in the doc that this section is planning-only and the work is
post-v0.4.
