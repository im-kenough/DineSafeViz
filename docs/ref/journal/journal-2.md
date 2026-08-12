# Journal 2

## 2026-08-12 — Documentation restructure to Diátaxis

### Task
Review all repo documentation, restructure to the Diátaxis framework, and
consolidate related documents. Out of scope: `docs/ref/arch/design-planning`.

### 2026-08-12 — Orientation and decisions
Surveyed `docs/`. Found a partial Diátaxis attempt (`how-to/`, `ref/`), plus
superseded `old-ignore/` trees and empty stubs.

Ran a platform keyword scan across in-scope docs. Finding: all install/deploy
how-to guides target Proxmox; only `1-workstation-v0.4.0.md` and some reference
docs (`azure-component-inventory`, `arch-dr`, `arch-checklist`) target Azure/AKS.

User decisions (via clarifying questions):
- Scope: restructure + full prose rewrite to the write-better-docs style guide.
- Layout: three quadrants — how-to, reference, explanation (no tutorials).
- Platform: Azure/AKS is the forward direction, but keep Proxmox how-to guides
  live and label Azure material as target-state (v0.4.0, in progress). Nothing
  working gets archived.
- Cruft: move superseded content (old-ignore trees, empty stubs, duplicate
  workstation file) to a single `docs/archive/` folder rather than deleting.
- Numbering: user asked to number each doc within its quadrant.

### 2026-08-12 — Design approved, spec written
Confirmed no static-site generator (no mkdocs) — plain Markdown, so restructure
is git mv + link fixes. Inbound links found in README.md, GEMINI.md,
.github/release-drafter.yml, infra/ansible/vault/example-secrets.yml.

Presented target tree (three quadrants, numbered docs) and file mapping. User
approved. Wrote spec to
`docs/superpowers/specs/2026-08-12-docs-diataxis-restructure-design.md`.
Self-review caught a banner relative-link bug (how-to instance sits one level
up from reference/explanation) — fixed inline. Did NOT commit the spec:
CLAUDE.md says commit only when asked.

### 2026-08-12 — Implementation plan written
User approved spec (and asked to number each doc). Wrote implementation plan to
`docs/superpowers/plans/2026-08-12-docs-diataxis-restructure.md`. Six tasks:
(1) scaffold + archive, (2) how-to quadrant, (3) reference quadrant,
(4) explanation quadrant, (5) docs landing page, (6) inbound link fixes +
verification. Adapted the TDD cycle to a reusable `scan_links` broken-link check
since this is docs, not code. Numbering baked in per quadrant.
