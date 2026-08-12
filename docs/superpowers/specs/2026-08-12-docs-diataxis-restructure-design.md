# Documentation restructure to Diátaxis — design

## Goal

Restructure all repository documentation to follow the Diátaxis framework,
consolidate related documents, rewrite the prose to the write-better-docs style
guide, and number the docs within each quadrant.

## Scope

**In scope:** everything under `docs/` except the exclusions below.

**Out of scope:**

- `docs/ref/arch/design-planning/` (explicit exclusion from the user).
- `docs/ref/journal/` (CLAUDE.md hardcodes this path — do not move).
- `docs/img/` files themselves (kept as-is; only links to them are updated).

## Decisions

- **Layout:** three Diátaxis quadrants — `how-to/`, `reference/`, `explanation/`.
  No `tutorials/` quadrant (none exist; an empty section adds noise).
- **Prose:** full rewrite of every in-scope doc to the write-better-docs style
  guide (Google Developer Style Guide, Google Word List, ASD-STE100). Diátaxis
  classification governs structure.
- **Platform:** Proxmox is the current, live deployment path and stays as the
  primary how-to guides. Azure/AKS is the forward direction (v0.4.0). Azure
  docs are kept but carry a clear "target-state (v0.4.0, in progress)" banner so
  readers are not misled.
- **Superseded content:** moved to `docs/archive/`, not deleted.
- **Numbering:** each quadrant's content docs get a numeric prefix that orders
  them. Each quadrant keeps an unnumbered `README.md` index.

## Target structure

```
docs/
├── README.md                          NEW documentation home (Diátaxis landing)
├── how-to/
│   ├── README.md
│   ├── 1-install/
│   │   ├── README.md
│   │   ├── 1-workstation.md
│   │   ├── 2-setup-proxmox.md
│   │   ├── 3-create-proxmox-template.md
│   │   ├── 4-setup-app.md
│   │   ├── 5-create-vm-image.md
│   │   └── 6-deploy.md
│   ├── 2-install-azure-target.md      target-state banner
│   ├── 3-verify-a-deployment.md
│   ├── 4-redeploy.md
│   ├── 5-administer.md
│   ├── 6-release.md
│   ├── 7-rotate-secrets.md
│   └── 8-troubleshoot.md              troubleshooting + known-issues
├── reference/
│   ├── README.md
│   ├── 1-data-mapping.md
│   └── 2-azure-component-inventory.md target-state banner
├── explanation/
│   ├── README.md                      arch index + DevOps tech-stack section
│   ├── 1-use-cases.md
│   ├── 2-application-architecture.md
│   ├── 3-data-architecture.md
│   ├── 4-infrastructure-as-code.md
│   ├── 5-network-architecture.md
│   ├── 6-security-architecture.md
│   ├── 7-ci-cd-architecture.md
│   ├── 8-disaster-recovery.md         target-state banner
│   ├── 9-monitoring-architecture.md
│   ├── 10-testing-architecture.md
│   └── 11-development-process.md      workflow + project-management
├── archive/
│   ├── README.md                      explains why these are archived
│   ├── old-ignore/                    from docs/old-ignore/
│   ├── arch-old-ignore/               from docs/ref/arch/old-ignore/
│   ├── arch-checklist.md              WAF planning artifact (references design-planning)
│   └── stubs/
│       ├── arch-env.md
│       ├── overview-iac.md
│       └── infra.md
└── ref/
    └── journal/                       UNCHANGED (CLAUDE.md path)
```

## File mapping

| Source | Destination | Action |
|---|---|---|
| `docs/how-to/1-install/*` | `docs/how-to/1-install/*` | Keep, rewrite prose |
| `docs/how-to/1-install/1-workstation-v0.4.0.md` | `docs/how-to/2-install-azure-target.md` | Move, add banner, rewrite |
| `docs/how-to/2-piv.md` | `docs/how-to/3-verify-a-deployment.md` | Rename, rewrite |
| `docs/how-to/3-redeploy-guide.md` | `docs/how-to/4-redeploy.md` | Rename, rewrite |
| `docs/how-to/4-admin-guide.md` | `docs/how-to/5-administer.md` | Rename, rewrite |
| `docs/how-to/5-release.md` | `docs/how-to/6-release.md` | Rename, rewrite |
| `docs/how-to/6-rotate-secrets.md` | `docs/how-to/7-rotate-secrets.md` | Rename, rewrite |
| `docs/ref/troubleshooting.md` + `docs/ref/infra/known-issues.md` | `docs/how-to/8-troubleshoot.md` | Consolidate, rewrite |
| `docs/ref/data.md` | `docs/reference/1-data-mapping.md` | Move, rewrite |
| `docs/ref/azure-component-inventory.md` | `docs/reference/2-azure-component-inventory.md` | Move, add banner, rewrite |
| `docs/ref/sys-analysis-design/use-cases.md` | `docs/explanation/1-use-cases.md` | Move, rewrite |
| `docs/ref/arch/arch-app.md` | `docs/explanation/2-application-architecture.md` | Move, rewrite |
| `docs/ref/arch/arch-data.md` | `docs/explanation/3-data-architecture.md` | Move, rewrite |
| `docs/ref/arch/arch-iac.md` | `docs/explanation/4-infrastructure-as-code.md` | Move, rewrite |
| `docs/ref/arch/arch-net.md` | `docs/explanation/5-network-architecture.md` | Move, rewrite |
| `docs/ref/arch/arch-security.md` | `docs/explanation/6-security-architecture.md` | Move, rewrite |
| `docs/ref/arch/arch-ci-cd.md` | `docs/explanation/7-ci-cd-architecture.md` | Move, rewrite |
| `docs/ref/arch/arch-dr.md` | `docs/explanation/8-disaster-recovery.md` | Move, add banner, rewrite |
| `docs/ref/arch/arch-monitoring.md` | `docs/explanation/9-monitoring-architecture.md` | Move, rewrite |
| `docs/ref/arch/arch-testing.md` | `docs/explanation/10-testing-architecture.md` | Move, rewrite |
| `docs/ref/workflow.md` + `docs/ref/project-management.md` | `docs/explanation/11-development-process.md` | Consolidate, rewrite |
| `docs/ref/arch/README.MD` | `docs/explanation/README.md` | Move, rewrite (index + tech stack) |
| `docs/old-ignore/` | `docs/archive/old-ignore/` | Move as-is (no rewrite) |
| `docs/ref/arch/old-ignore/` | `docs/archive/arch-old-ignore/` | Move as-is (no rewrite) |
| `docs/ref/arch/arch-checklist.md` | `docs/archive/arch-checklist.md` | Move as-is |
| `docs/ref/arch/arch-env.md` | `docs/archive/stubs/arch-env.md` | Move as-is (empty stub) |
| `docs/ref/arch/overview-iac.md` | `docs/archive/stubs/overview-iac.md` | Move as-is (empty stub) |
| `docs/ref/infra/infra.md` | `docs/archive/stubs/infra.md` | Move as-is (empty stub) |

New files: `docs/README.md`, `docs/how-to/README.md`, `docs/reference/README.md`,
`docs/archive/README.md`.

## Inbound link updates (outside `docs/`)

Moving files breaks links from these files. Update each:

- `README.md` (repo root): links to `docs/ref/arch/arch-iac.md`,
  `docs/ref/arch/arch-app.md`, `docs/ref/arch/README.MD`,
  `docs/ref/arch/arch-security.md`, `docs/ref/arch/arch-monitoring.md`,
  `docs/how-to/1-install/README.md`, `docs/how-to/3-redeploy-guide.md`.
- `GEMINI.md`: check and update any `docs/` links.
- `.github/release-drafter.yml`: check and update any `docs/` links.
- `infra/ansible/vault/example-secrets.yml`: check and update any `docs/` links.

`CLAUDE.md` journal path is not a doc link and stays unchanged.

## Prose rewrite rules (write-better-docs)

Apply per the loaded skill:

- Second person, active voice, present tense.
- Sentences ≤25 words, paragraphs ≤6 sentences, one instruction per sentence.
- Conditions before instructions ("If x, do y"). No semicolons. Oxford comma.
- Sentence case headings. Descriptive link text.
- Word list: "use" not "utilize/leverage", "for example" not "e.g.",
  "such as" not "i.e.", "earlier/later" not "above/below", "because" not "as".
- Diátaxis boundaries: no step-by-step procedures inside reference or
  explanation docs — link to the how-to guide instead. No long conceptual
  digressions inside how-to guides — link to the explanation doc instead.

## Target-state banner (verbatim)

Add to `2-install-azure-target.md`, `reference/2-azure-component-inventory.md`,
and `explanation/8-disaster-recovery.md`, directly under the H1. Adjust the
relative link per the doc's location:

- In `reference/` and `explanation/` docs, use `../how-to/1-install/README.md`.
- In `how-to/2-install-azure-target.md`, use `1-install/README.md`.

```
> [!NOTE]
> **Target state (v0.4.0, in progress).** This document describes the planned
> Azure/AKS architecture, not the currently deployed Proxmox environment. For
> the live deployment, see the [Proxmox install guide](RELATIVE-PATH).
```

## Cross-link updates (inside `docs/`)

- `explanation/3-data-architecture.md` links to `reference/1-data-mapping.md`
  (currently `../data.md`).
- Every quadrant `README.md` links to its numbered docs.
- `docs/README.md` links to the three quadrant indexes and explains Diátaxis.
- All existing intra-doc relative links re-pointed to new paths.

## Verification criteria

1. `find docs -name '*.md'` shows the target tree; no in-scope source paths
   remain except `docs/ref/journal/`.
2. No broken relative Markdown links inside `docs/` (link-check pass).
3. No inbound link from `README.md`, `GEMINI.md`, `.github/release-drafter.yml`,
   or `infra/ansible/vault/example-secrets.yml` points to an old path.
4. Every rewritten doc passes the write-better-docs documentation checklist.
5. Each quadrant has a `README.md` index that links every numbered doc.
6. `git mv` used for moves so history is preserved where content is unchanged.

## Non-goals

- No content invention. If a doc is a stub or says "coming soon", it stays that
  way (rewritten for style, not filled in).
- No touching `design-planning/`, the journal, or image files.
- No new tooling (no static-site generator).
