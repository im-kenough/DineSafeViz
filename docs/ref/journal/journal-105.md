# Journal 105

## 2026-06-22 — Consolidate AKS design docs into arch-design-aks.md

### Goal

Tighten the requirements in
`docs/ref/arch/design-planning/arch-design-aks.md` and fold the
design-rationale content from `arch-design-decision.md` into it so it
reads as one cohesive document. Begin the doc with a requirements
section describing the full prod and stg environments.

### 2026-06-22 — Brainstorming / context gathering

- Read `arch-design-aks.md`, `arch-design-decision.md`,
  `arch-design-planning.md`, and the folder `Readme.md`.
- Finding: `arch-design-aks.md` already contains two layers — a rough
  "Requirements" draft (lines 1-127) and a `# old, ignore` block
  (lines 132-511) that is byte-for-byte identical to
  `arch-design-decision.md`. So "folding in the decision doc" means
  promoting that block and reconciling it with the requirements draft;
  there is no third copy.
- Contradiction surfaced: the requirements draft specified passive DR
  *clusters* (full node pools) for prod and stg in west-us-2, while the
  decision doc describes passive-cold (data-only, no standing cluster).
  Budget figures also differed ($100/mo cap vs $25-50 steady-state) and
  staging DR differed (cluster vs LRS-only / no DR).
- `arch-checklist.md` is referenced repeatedly but does not exist. The
  implementation spec `docs/superpowers/specs/2026-06-09-aks-deployment-design.md`
  does exist.

### Decisions

- DR model: **passive-cold (data only)** for both prod and stg. No
  standing DR cluster; the west-us-2 environment is provisioned from
  IaC at failover. Generic term: backup-and-restore (coldest DR tier);
  Azure term: passive-cold. User will provision the DR environment when
  DR is activated.
- Because staging also gets passive-cold DR, staging WAL/backups must
  use GRS (cross-region) too — this conflicts with the decision doc's
  "LRS for staging WAL" cost note, to be reconciled during the fold-in.

### 2026-06-22 — Edits

- Revised the prod and stg DR bullets in the requirements section of
  `arch-design-aks.md` from passive DR clusters to passive-cold (data
  only). Two `Edit` calls.
- User chose: fold requirements + decision doc only (planning.md stays
  separate); consolidate without deleting source files.
- Rewrote `arch-design-aks.md` as one cohesive doc: intro/BLUF →
  Requirements → AKS cluster configuration → Context → Scope →
  Reference architectures → Conformance table → WAF pillar assessment →
  out-of-scope → Decision log → References. Removed the `# old, ignore`
  block (the duplicate of `arch-design-decision.md`); promoted that
  content into the live doc. `arch-design-decision.md` left in place per
  user choice.
- Reconciled two contradictions while folding:
  - Budget: $100/mo hard cap with 50/80/100% alerts (FinOps
    requirements) is authoritative; "$25-50 steady-state" kept as the
    expectation. Replaced the decision doc's "80% of $50/mo" alert line.
  - Staging WAL changed from LRS to GRS (staging now has passive-cold
    DR); updated the cost-optimization bullet.
  - Filled AKS-config TBDs from known decisions (B2s, Standard SSD E10).
  - Added a Decision log entry dated 2026-06-22 for the DR-model choice.
  - Fixed the implementation-spec relative link: was `../../superpowers/`
    (resolves to docs/ref/superpowers, broken); now `../../../superpowers/`
    (verified resolves to the existing spec).
- Verified: spec link resolves; no `# old, ignore` block remains; file
  is 486 lines.

### Open items for next iteration

- `arch-checklist.md` is still referenced by the TODO blocks and does
  not exist. Left intact (cleanup not authorized this pass).
- `arch-design-decision.md` is now a redundant duplicate; user will
  remove it.
- Folder `Readme.md` index may need updating once the dust settles.
