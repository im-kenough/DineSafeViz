# Journal Entry 104

- **Timestamp**: 2026-06-22 11:00
- **Summary**: Planning the consolidation of AKS design-planning docs into a single cohesive `arch-design-aks.md`, starting with a requirements section describing the full prod + stg environment.
- **Task**: User wants `docs/ref/arch/design-planning/arch-design-aks.md` to become the one cohesive AKS deployment document. Fold in `arch-design-decision.md` (and possibly others), pull relevant guidance from `arch-design-planning.md`, and begin with a requirements section listing the full prod/stg environment.

## Context gathered

Read all four docs in `docs/ref/arch/design-planning/`:

- `arch-design-aks.md` (21KB, untracked/NEW) — TARGET. Top (lines 1-127) = new requirements + AKS sizing (env topology, FinOps, phases). Bottom (lines 130+, marked "old, ignore") = verbatim duplicate of `arch-design-decision.md`.
- `arch-design-decision.md` (17KB) — Reference architectures + WAF pillar assessment + AKS Baseline conformance table. "Design-rationale companion to the spec."
- `arch-design-planning.md` (49KB) — WAF technology-choices doc (compute, container, hybrid, identity, storage, data store, analytics, networking, messaging, integration). The guidance the user went through.
- `Readme.md` (6.7KB) — WAF pillars + OE design patterns + maturity model.
- `arch-design-decisions-brief.md` — deleted (git status shows `D`).

## Inconsistencies found across docs (to surface during brainstorming)

- **Region**: aks.md says prod/stg in east-us-2, DR in west-us-2; planning.md data-store section says "Canada Central only" / "keep data in Canada".
- **Budget**: aks.md requirements say $100/mo (warn 50%/80%, shutdown 100%); decision.md says $50/mo cap, alert at 80%.
- **DR RTO**: decision.md says RTO ≤ 4h; planning.md data-store says RTO ≈ 20-30 min.
- **OS disk tier**: planning.md summary says Standard HDD→SSD Q1 2028, but its disk-types section says Standard SSD; decision.md says Standard SSD (E10).
- **VM size**: aks.md says TBD; decision.md says B2s burstable.

## Next

Brainstorming skill engaged. Asking scope question first: which docs fold into aks.md vs. stay as linked references.
