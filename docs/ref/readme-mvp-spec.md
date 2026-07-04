# README MVP Revision Spec

Instructions for an LLM coding agent to revise [`README.md`](../README.md) (currently
on branch `feat/main-readme-rf`, the on-prem deployment). This README is intended to
become the project's `main` README and is the first thing a recruiter, hiring manager,
or engineer sees.

> All relative links in this spec are written from this file's location
> (`docs/readme-mvp-spec.md`) and were verified to resolve. When you edit the README
> (which lives at the repo root), recompute paths relative to the **repo root**.

## Goal

Maximize **clarity**. The README is the front door: a reader should understand, in
under 60 seconds, what the project is, why it exists, what it's built with, what state
it's in, and where to go for depth. The deep docs under [`docs/`](.) already exist —
the README orients and links; it does not duplicate them.

## README quality bar (apply to every change)

- **Readable.** Short paragraphs and lists over walls of text. Lead each section with
  its point. A skimmer reading only headings and first lines should still get it.
- **Well-formatted.** Consistent heading hierarchy, fenced code blocks for commands,
  a status table instead of scattered inline notes, alt text on every image.
- **Concise but information-dense.** Cut filler; keep specifics. Every sentence should
  carry a fact (a tool, a number, a state, a link). No marketing padding.
- **Link generously, to the right depth.** Name a component, service, doc, or external
  tool → link it. Link to files, directories, and authoritative external sites
  (Docker, Terraform, the DineSafe dataset) so the reader can go one level deeper
  without the README having to explain everything inline.
- **No broken links.** Every relative link must resolve from the repo root, and every
  image path must point to a real file. **Verify before finishing** (see
  [Definition of done](#definition-of-done)).

## Rules for the implementer

- Do **not** fabricate facts. Where a value is unknown (live demo URL, real version
  numbers, build status), insert a clearly marked `<!-- TODO: ... -->` for the human,
  or omit the element. An empty placeholder like `v x.y.z` is worse than omitting it.
- Preserve the author's voice; this is a personal-project README, not marketing copy.
- Keep the existing screenshots and the architecture diagram.

---

## P0 — Correctness and credibility (must fix)

### P0.1 — Broken link to secrets.yml
**Where:** Information security section (~line 71).
**Problem:** The link path is `DineSafeViz/infra/ansible/vault/secrets.yml`. There is
no `DineSafeViz/` subdirectory; the path is relative to the repo root, so it 404s on
GitHub.
**Fix:** Point it at [`infra/ansible/vault/secrets.yml`](../infra/ansible/vault/secrets.yml)
(from the README at repo root, the path is `infra/ansible/vault/secrets.yml`).

### P0.2 — State that committed secrets are encrypted
**Where:** Information security section.
**Problem:** "Secrets are stored in secrets.yml" can alarm a reviewer who sees a
`secrets.yml` tracked in git. It is in fact **Ansible Vault AES256-encrypted**
(verified), which is good practice and worth saying.
**Fix:** Reword, e.g.: "Secrets are stored Ansible Vault-encrypted in
[`infra/ansible/vault/secrets.yml`](../infra/ansible/vault/secrets.yml) and injected
into the `.env` file at deploy time via Ansible." Point to the template
[`infra/ansible/vault/example-secrets.yml`](../infra/ansible/vault/example-secrets.yml).

### P0.3 — Remove placeholder "Evolution" entries
**Where:** Evolution section (~lines 90-95), entries read `v x.y.z`.
**Fix:** Replace with real version/date entries, or cut the section until real content
exists. Do not ship `x.y.z`. (Recommended: cut for the MVP; the Roadmap link already
covers forward-looking status.)

### P0.4 — Spelling / grammar
- "selfhosted" → "self-hosted" (both occurrences, ~lines 6, 25).
- "Small foot print" → "Small footprint" (~line 27).
- Standardize visualize/visualise → **"visualize"** (repo mixes both: ~lines 35, 51).
- "configuration are retrieved" → "configuration **is** retrieved" (~line 71).
- Delete the stray bare path under Monitoring (~line 76, `docs/ref/arch/arch-monitoring.md`);
  the heading above it is already a link.

---

## P1 — Clarity and structure (should fix)

### P1.1 — Strengthen the opening block (does the most work)
**Where:** Lines 1-8.
**Fix:** After the one-line description add, in this order:
- One sentence on *why* the project exists (the engineering goal it demonstrates:
  end-to-end IaC + container orchestration of a real, 26-year public dataset).
- A **Tech stack** one-liner, linking the main tools:
  [Docker](https://www.docker.com/),
  [PostgreSQL](https://www.postgresql.org/),
  [Grafana](https://grafana.com/),
  [Terraform](https://www.terraform.io/),
  [Packer](https://www.packer.io/),
  [Ansible](https://www.ansible.com/),
  [Proxmox VE](https://www.proxmox.com/en/proxmox-virtual-environment).
- A **Status** callout: this branch is the on-prem (Proxmox) deployment; an AKS
  migration is in design (see [P1.3](#p13--surface-the-aks-migration-forward-looking-devops-signal)).
- A `<!-- TODO: live demo URL -->` if a public instance is planned.
- Link the data source: the [City of Toronto DineSafe open dataset](https://open.toronto.ca/dataset/dinesafe/).

### P1.2 — Consolidate the "Coming Soon (™️)" markers into a Status table
**Where:** ~lines 38, 73.
**Fix:** Replace scattered inline notes with one **Project status** table near the top,
e.g.:

| Component | State |
|---|---|
| Inspection results | Done |
| Analytics dashboard ([Grafana](https://grafana.com/)) | Done |
| Daily data refresh | In progress |
| Monitoring | Planned |
| AKS deployment | In design |

Keep the honesty; make it look deliberate. Remove the inline "Coming Soon" notes once
captured here.

### P1.3 — Surface the AKS migration (forward-looking DevOps signal)
**Problem:** The strongest portfolio signal — real cloud architecture work in progress
— is currently invisible in the README.
**Fix:** Add a short "What's next: AKS migration" subsection (under Architecture or
Roadmap) linking the existing design docs:
[AKS deployment design](superpowers/specs/2026-06-09-aks-deployment-design.md) and
[AKS deployment plan](superpowers/plans/2026-06-09-aks-deployment.md). One or two
sentences; let the docs carry the detail. If the planned Azure diagram is exported
from [`docs/img/azure.drawio`](img/azure.drawio), embed it; otherwise add
`<!-- TODO: export azure.drawio to png -->`.

### P1.4 — Make "Getting Started" name its entry point
**Where:** Getting Started (~lines 79-82).
**Fix:** Add a one-line lead-in: the
[install guide](how-to/1-install/README.md) is the from-scratch start; the
[redeploy guide](how-to/3-redeploy-guide.md) is for existing infrastructure. If a
quick local `docker compose up` path exists (see [`docker-compose.yml`](../docker-compose.yml)),
add a minimal fenced "Run locally" snippet; if DB seeding is required first, say so in
one line rather than implying it's a single command.

---

## P2 — Nice to have (after P0/P1)

- **P2.1** Add status badges (build, license) once CI exists. Skip until real.
- **P2.2** Standardize doc-link casing: [`docs/ref/arch/README.MD`](ref/arch/README.MD)
  uses uppercase `.MD`. Rename to `README.md` and update links, or leave consistently.
- **P2.3** Link the deeper arch docs that exist but aren't surfaced from the README
  (link only the reader-ready ones; skip stubs):
  [design decisions](ref/arch/arch-design-decision.md),
  [networking](ref/arch/arch-net.md),
  [CI/CD](ref/arch/arch-ci-cd.md),
  [disaster recovery](ref/arch/arch-dr.md),
  [testing](ref/arch/arch-testing.md).
- **P2.4** Add a `LICENSE` and reference it if the repo is public.

---

## Suggested section order

1. Title + one-line description + why-it-exists sentence
2. Tech stack (one line) + Project status table
3. Screenshot (home page)
4. Features (with screenshots) — keep
5. Architecture (app services, [IaC](ref/arch/arch-iac.md),
   [security](ref/arch/arch-security.md), [monitoring](ref/arch/arch-monitoring.md))
   — keep; apply P0/P1 fixes
6. What's next: AKS migration ([P1.3](#p13--surface-the-aks-migration-forward-looking-devops-signal))
7. Getting Started ([P1.4](#p14--make-getting-started-name-its-entry-point))
8. Roadmap (keep the [project board](https://github.com/users/im-kenough/projects/11) link)
9. Evolution — only if real entries exist; otherwise omit

## Definition of done

- [ ] All P0 items applied.
- [ ] Every relative link resolves from the repo root, and every image path points to a
      real file. Verify mechanically, e.g. from the repo root:
      ```bash
      grep -oE '\]\(([^)]+)\)' README.md | sed -E 's/^\]\(|\)$//g' \
        | grep -vE '^https?://|^#' \
        | while read -r p; do [ -e "$p" ] || echo "BROKEN: $p"; done
      ```
- [ ] No placeholder text of the form `x.y.z`; unknowns are explicit `<!-- TODO -->`.
- [ ] A reader can answer "what is this, why, what stack, what state, where's the
      depth" from the top third of the README alone.
