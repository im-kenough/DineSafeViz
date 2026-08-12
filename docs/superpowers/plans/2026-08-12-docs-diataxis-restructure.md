# Documentation Diátaxis Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `docs/` into three Diátaxis quadrants (how-to, reference, explanation), consolidate related documents, rewrite the prose to the write-better-docs style guide, number the docs, and archive superseded content — without breaking any inbound or intra-doc links.

**Architecture:** Plain Markdown, no static-site generator. Moves use `git mv` to preserve history. Work proceeds one quadrant per task so each is independently reviewable. A reusable link-check command gates every task.

**Tech Stack:** Markdown, git, bash (find/grep) for verification.

## Global Constraints

Copied verbatim from `docs/superpowers/specs/2026-08-12-docs-diataxis-restructure-design.md`. Every task inherits these.

- **Do not touch** `docs/ref/arch/design-planning/`, `docs/ref/journal/`, or the image files in `docs/img/` (update links to images, not the images).
- **Three quadrants only:** `how-to/`, `reference/`, `explanation/`. No `tutorials/`.
- **Numbering:** each quadrant's content docs get a numeric prefix ordering them. Each quadrant keeps an unnumbered `README.md` index.
- **Prose rewrite (write-better-docs):** second person, active voice, present tense; sentences ≤25 words; paragraphs ≤6 sentences; one instruction per sentence; conditions before instructions; no semicolons; Oxford comma; sentence-case headings; descriptive link text. Word substitutions: "use" not "utilize/leverage", "for example" not "e.g.", "such as" not "i.e.", "earlier/later" not "above/below", "because" (for cause) not "as".
- **Diátaxis boundaries:** no step-by-step procedures inside reference/explanation — link to the how-to. No long conceptual digressions inside how-to — link to the explanation.
- **No content invention.** Stubs and "coming soon" stay that way (rewritten for style only).
- **Platform:** Proxmox is live; Azure/AKS is target-state. Banner the three Azure-target docs.
- **Commits:** commit at the end of each task. Use `git mv` for moves.

### Target-state banner

Place directly under the H1 of `how-to/2-install-azure-target.md`, `reference/2-azure-component-inventory.md`, and `explanation/8-disaster-recovery.md`. Set `RELATIVE-PATH` to `1-install/README.md` for the how-to doc, `../how-to/1-install/README.md` for the reference and explanation docs.

```
> [!NOTE]
> **Target state (v0.4.0, in progress).** This document describes the planned
> Azure/AKS architecture, not the currently deployed Proxmox environment. For
> the live deployment, see the [Proxmox install guide](RELATIVE-PATH).
```

### Reusable verification: broken relative-link scan

Run from repo root. Reports any relative Markdown link whose target file does not exist. A clean run prints nothing.

```bash
scan_links() {
  find docs -name '*.md' ! -path 'docs/ref/journal/*' ! -path 'docs/ref/arch/design-planning/*' -print0 \
  | while IFS= read -r -d '' f; do
      grep -oE '\]\(([^)]+)\)' "$f" | sed -E 's/^\]\(//; s/\)$//' \
      | grep -vE '^(https?:|#|mailto:)' | sed -E 's/#.*$//' \
      | while IFS= read -r link; do
          [ -z "$link" ] && continue
          target="$(dirname "$f")/$link"
          [ -e "$target" ] || echo "BROKEN: $f -> $link"
        done
    done
}
scan_links
```

---

### Task 1: Scaffold quadrants and archive superseded content

Mechanical moves only — no prose changes. Establishes the skeleton so later tasks land files in place.

**Files:**
- Create dirs: `docs/how-to/`, `docs/reference/`, `docs/explanation/`, `docs/archive/`, `docs/archive/stubs/`
- Move: `docs/old-ignore/` → `docs/archive/old-ignore/`
- Move: `docs/ref/arch/old-ignore/` → `docs/archive/arch-old-ignore/`
- Move: `docs/ref/arch/arch-checklist.md` → `docs/archive/arch-checklist.md`
- Move: `docs/ref/arch/arch-env.md` → `docs/archive/stubs/arch-env.md`
- Move: `docs/ref/arch/overview-iac.md` → `docs/archive/stubs/overview-iac.md`
- Move: `docs/ref/infra/infra.md` → `docs/archive/stubs/infra.md`
- Create: `docs/archive/README.md`

- [ ] **Step 1: Create the directories**

```bash
cd /home/admin-ubuntu/SCM/DineSafeViz
mkdir -p docs/reference docs/explanation docs/archive/stubs
```

- [ ] **Step 2: git mv the superseded trees and stubs**

```bash
git mv docs/old-ignore docs/archive/old-ignore
git mv docs/ref/arch/old-ignore docs/archive/arch-old-ignore
git mv docs/ref/arch/arch-checklist.md docs/archive/arch-checklist.md
git mv docs/ref/arch/arch-env.md docs/archive/stubs/arch-env.md
git mv docs/ref/arch/overview-iac.md docs/archive/stubs/overview-iac.md
git mv docs/ref/infra/infra.md docs/archive/stubs/infra.md
```

- [ ] **Step 3: Write the archive README**

`docs/archive/README.md`:

```markdown
# Archive

These documents are superseded or empty and are kept only for history. They are
not part of the maintained documentation set. Do not link to them from the live
docs.

- `old-ignore/`, `arch-old-ignore/`: earlier drafts replaced by the current
  how-to, reference, and explanation docs.
- `arch-checklist.md`: an Azure Well-Architected reading checklist that belongs
  to the out-of-scope AKS design-planning work.
- `stubs/`: empty or near-empty placeholders (`arch-env.md`, `overview-iac.md`,
  `infra.md`).
```

- [ ] **Step 4: Verify the tree**

Run: `find docs/archive -type f | sort`
Expected: the six moved items plus `docs/archive/README.md`. Confirm the source paths no longer exist: `ls docs/old-ignore docs/ref/arch/old-ignore 2>&1` should report "No such file".

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: scaffold Diátaxis quadrants and archive superseded content"
```

---

### Task 2: How-to quadrant — move, consolidate, rewrite

**Files:**
- Keep in place, rewrite: `docs/how-to/1-install/{README.md,1-workstation.md,2-setup-proxmox.md,3-create-proxmox-template.md,4-setup-app.md,5-create-vm-image.md,6-deploy.md}`
- Move + banner + rewrite: `docs/how-to/1-install/1-workstation-v0.4.0.md` → `docs/how-to/2-install-azure-target.md`
- Move + rewrite: `docs/how-to/2-piv.md` → `docs/how-to/3-verify-a-deployment.md`
- Move + rewrite: `docs/how-to/3-redeploy-guide.md` → `docs/how-to/4-redeploy.md`
- Move + rewrite: `docs/how-to/4-admin-guide.md` → `docs/how-to/5-administer.md`
- Move + rewrite: `docs/how-to/5-release.md` → `docs/how-to/6-release.md`
- Move + rewrite: `docs/how-to/6-rotate-secrets.md` → `docs/how-to/7-rotate-secrets.md`
- Consolidate + rewrite: `docs/ref/troubleshooting.md` + `docs/ref/infra/known-issues.md` → `docs/how-to/8-troubleshoot.md`
- Create: `docs/how-to/README.md`

**Interfaces:**
- Produces destination paths that Task 5 (indexes) and Task 6 (inbound links) rely on: `how-to/1-install/README.md`, `how-to/2-install-azure-target.md`, `how-to/3-verify-a-deployment.md`, `how-to/4-redeploy.md`, `how-to/5-administer.md`, `how-to/6-release.md`, `how-to/7-rotate-secrets.md`, `how-to/8-troubleshoot.md`.

- [ ] **Step 1: git mv the renamed guides**

```bash
cd /home/admin-ubuntu/SCM/DineSafeViz
git mv docs/how-to/1-install/1-workstation-v0.4.0.md docs/how-to/2-install-azure-target.md
git mv docs/how-to/2-piv.md docs/how-to/3-verify-a-deployment.md
git mv docs/how-to/3-redeploy-guide.md docs/how-to/4-redeploy.md
git mv docs/how-to/4-admin-guide.md docs/how-to/5-administer.md
git mv docs/how-to/5-release.md docs/how-to/6-release.md
git mv docs/how-to/6-rotate-secrets.md docs/how-to/7-rotate-secrets.md
```

- [ ] **Step 2: Consolidate troubleshooting**

Create `docs/how-to/8-troubleshoot.md`. Merge the content of `docs/ref/troubleshooting.md` (each symptom → cause → fix stays a section) and append the content of `docs/ref/infra/known-issues.md` under a `## Known issues` section. Then remove the two sources:

```bash
git rm docs/ref/troubleshooting.md docs/ref/infra/known-issues.md
```

Rewrite the merged prose to the style guide. Keep each problem as `## <symptom>` with a `### Fix` subsection.

- [ ] **Step 3: Rewrite each how-to doc to the style guide**

For every file listed under this task, apply the Global Constraints prose rules. Per-file notes:
- `1-install/README.md`: keep the ordered step list; verify each link points to the sibling step file. Update the H1 to sentence case.
- `1-install/1-workstation.md` through `6-deploy.md`: these are Proxmox steps (live). Keep commands verbatim inside code fences — do not reword code. Reword only prose. Put conditions before instructions.
- `2-install-azure-target.md`: add the target-state banner (`RELATIVE-PATH` = `1-install/README.md`). Keep Azure commands verbatim.
- `3-verify-a-deployment.md` through `7-rotate-secrets.md`: rewrite prose; keep commands verbatim.
- `8-troubleshoot.md`: as built in Step 2.

- [ ] **Step 4: Write the how-to index**

`docs/how-to/README.md`:

```markdown
# How-to guides

Task-oriented guides for operating DineSafeViz.

1. [Install (Proxmox)](1-install/README.md)
2. [Install on Azure (target state)](2-install-azure-target.md)
3. [Verify a deployment](3-verify-a-deployment.md)
4. [Redeploy the application](4-redeploy.md)
5. [Administer DineSafeViz](5-administer.md)
6. [Release process](6-release.md)
7. [Rotate secrets](7-rotate-secrets.md)
8. [Troubleshoot](8-troubleshoot.md)
```

- [ ] **Step 5: Verify links and checklist**

Run the `scan_links` function (see Global Constraints). Expected: no `BROKEN` lines involving `docs/how-to/`. Spot-check three rewritten docs against the write-better-docs documentation checklist (no "e.g.", no "above/below", sentences ≤25 words).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: move and rewrite how-to guides into Diátaxis how-to quadrant"
```

---

### Task 3: Reference quadrant — move, banner, rewrite

**Files:**
- Move + rewrite: `docs/ref/data.md` → `docs/reference/1-data-mapping.md`
- Move + banner + rewrite: `docs/ref/azure-component-inventory.md` → `docs/reference/2-azure-component-inventory.md`
- Create: `docs/reference/README.md`

**Interfaces:**
- Produces `reference/1-data-mapping.md` (Task 4's data-architecture doc links to it) and `reference/2-azure-component-inventory.md`.

- [ ] **Step 1: git mv the reference docs**

```bash
cd /home/admin-ubuntu/SCM/DineSafeViz
git mv docs/ref/data.md docs/reference/1-data-mapping.md
git mv docs/ref/azure-component-inventory.md docs/reference/2-azure-component-inventory.md
```

- [ ] **Step 2: Rewrite to the style guide**

- `1-data-mapping.md`: this is pure reference (column dictionary, sample rows, source URLs). Keep the tables and sample data intact. Rewrite only the surrounding prose. Do not add procedures.
- `2-azure-component-inventory.md`: add the target-state banner (`RELATIVE-PATH` = `../how-to/1-install/README.md`). Keep the inventory tables intact; rewrite prose.

- [ ] **Step 3: Write the reference index**

`docs/reference/README.md`:

```markdown
# Reference

Information-oriented, factual lookup documents.

1. [Data mapping](1-data-mapping.md)
2. [Azure component inventory](2-azure-component-inventory.md)
```

- [ ] **Step 4: Verify links**

Run `scan_links`. Expected: no `BROKEN` lines involving `docs/reference/`.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: move and rewrite reference docs into Diátaxis reference quadrant"
```

---

### Task 4: Explanation quadrant — move, consolidate, rewrite

**Files:**
- Move + rewrite: `docs/ref/sys-analysis-design/use-cases.md` → `docs/explanation/1-use-cases.md`
- Move + rewrite: `docs/ref/arch/arch-app.md` → `docs/explanation/2-application-architecture.md`
- Move + rewrite: `docs/ref/arch/arch-data.md` → `docs/explanation/3-data-architecture.md`
- Move + rewrite: `docs/ref/arch/arch-iac.md` → `docs/explanation/4-infrastructure-as-code.md`
- Move + rewrite: `docs/ref/arch/arch-net.md` → `docs/explanation/5-network-architecture.md`
- Move + rewrite: `docs/ref/arch/arch-security.md` → `docs/explanation/6-security-architecture.md`
- Move + rewrite: `docs/ref/arch/arch-ci-cd.md` → `docs/explanation/7-ci-cd-architecture.md`
- Move + banner + rewrite: `docs/ref/arch/arch-dr.md` → `docs/explanation/8-disaster-recovery.md`
- Move + rewrite: `docs/ref/arch/arch-monitoring.md` → `docs/explanation/9-monitoring-architecture.md`
- Move + rewrite: `docs/ref/arch/arch-testing.md` → `docs/explanation/10-testing-architecture.md`
- Consolidate + rewrite: `docs/ref/workflow.md` + `docs/ref/project-management.md` → `docs/explanation/11-development-process.md`
- Move + rewrite: `docs/ref/arch/README.MD` → `docs/explanation/README.md`

**Interfaces:**
- Produces all `explanation/*` paths that Task 5 and Task 6 link to.

- [ ] **Step 1: git mv the architecture docs**

```bash
cd /home/admin-ubuntu/SCM/DineSafeViz
git mv docs/ref/sys-analysis-design/use-cases.md docs/explanation/1-use-cases.md
git mv docs/ref/arch/arch-app.md docs/explanation/2-application-architecture.md
git mv docs/ref/arch/arch-data.md docs/explanation/3-data-architecture.md
git mv docs/ref/arch/arch-iac.md docs/explanation/4-infrastructure-as-code.md
git mv docs/ref/arch/arch-net.md docs/explanation/5-network-architecture.md
git mv docs/ref/arch/arch-security.md docs/explanation/6-security-architecture.md
git mv docs/ref/arch/arch-ci-cd.md docs/explanation/7-ci-cd-architecture.md
git mv docs/ref/arch/arch-dr.md docs/explanation/8-disaster-recovery.md
git mv docs/ref/arch/arch-monitoring.md docs/explanation/9-monitoring-architecture.md
git mv docs/ref/arch/arch-testing.md docs/explanation/10-testing-architecture.md
git mv docs/ref/arch/README.MD docs/explanation/README.md
```

- [ ] **Step 2: Consolidate development process**

Create `docs/explanation/11-development-process.md`. Merge `docs/ref/workflow.md` (coding standards, guidelines, sprint process) and `docs/ref/project-management.md` (projects, issue lifecycle). Structure: `## Coding standards`, `## Guidelines`, `## Sprint planning and execution`, `## Project management` (issue lifecycle, dashboards). Remove the sources:

```bash
git rm docs/ref/workflow.md docs/ref/project-management.md
```

- [ ] **Step 3: Rewrite each explanation doc to the style guide**

Apply the Global Constraints prose rules. Per-file notes:
- `3-data-architecture.md`: fix the data-mapping link. It currently points to `../data.md`; change to `../reference/1-data-mapping.md`.
- `8-disaster-recovery.md`: add the target-state banner (`RELATIVE-PATH` = `../how-to/1-install/README.md`).
- `README.md` (explanation index): rebuild the table of contents to point at the numbered explanation docs (see Step 4). Keep the DevOps-lifecycle "Tech stack" section; rewrite its prose. Keep `TODO`/"coming soon" notes as-is (no content invention).
- All arch docs: keep diagrams, tables, and code fences intact; rewrite prose only. Where a doc contains procedures, move them out to the relevant how-to and link instead.

- [ ] **Step 4: Build the explanation index**

Ensure `docs/explanation/README.md` opens with:

```markdown
# Explanation

Understanding-oriented discussion of how DineSafeViz is designed and why.

1. [Use cases](1-use-cases.md)
2. [Application architecture](2-application-architecture.md)
3. [Data architecture](3-data-architecture.md)
4. [Infrastructure as code](4-infrastructure-as-code.md)
5. [Network architecture](5-network-architecture.md)
6. [Security architecture](6-security-architecture.md)
7. [CI/CD architecture](7-ci-cd-architecture.md)
8. [Disaster recovery and resiliency](8-disaster-recovery.md)
9. [Monitoring architecture](9-monitoring-architecture.md)
10. [Testing architecture](10-testing-architecture.md)
11. [Development process](11-development-process.md)
```

Keep the existing "Tech stack" section below the index.

- [ ] **Step 5: Remove now-empty source directories**

```bash
rmdir docs/ref/arch docs/ref/sys-analysis-design docs/ref/infra 2>/dev/null || true
```

Note: `docs/ref/journal/` stays. If `rmdir` reports a directory is not empty, stop and inspect — an in-scope file was missed.

- [ ] **Step 6: Verify links and checklist**

Run `scan_links`. Expected: no `BROKEN` lines involving `docs/explanation/`. Confirm `docs/explanation/3-data-architecture.md` links to `../reference/1-data-mapping.md`, not `../data.md`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "docs: move and rewrite architecture docs into Diátaxis explanation quadrant"
```

---

### Task 5: Documentation home and cross-quadrant navigation

**Files:**
- Create: `docs/README.md`

- [ ] **Step 1: Write the documentation landing page**

`docs/README.md`:

```markdown
# DineSafeViz documentation

This documentation follows the [Diátaxis](https://diataxis.fr/) framework. It
separates content by what you need:

- **[How-to guides](how-to/README.md):** task-oriented steps to install,
  deploy, operate, and troubleshoot the application.
- **[Reference](reference/README.md):** factual lookup — data mapping and the
  Azure component inventory.
- **[Explanation](explanation/README.md):** the architecture and the reasoning
  behind the design.

## Platform status

The live deployment runs on self-hosted Proxmox. The Azure/AKS architecture is
the target state for v0.4.0 and is in progress. Documents that describe the
target state carry a note at the top.
```

- [ ] **Step 2: Verify links**

Run `scan_links`. Expected: no `BROKEN` lines.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs: add Diátaxis documentation landing page"
```

---

### Task 6: Fix inbound links and final verification

**Files:**
- Modify: `README.md` (repo root)
- Modify: `GEMINI.md`
- Modify: `.github/release-drafter.yml`
- Modify: `infra/ansible/vault/example-secrets.yml`

**Interfaces:**
- Consumes every destination path produced by Tasks 2–5.

- [ ] **Step 1: Find every inbound reference**

```bash
cd /home/admin-ubuntu/SCM/DineSafeViz
grep -rnE 'docs/(ref|how-to)/' README.md GEMINI.md .github/release-drafter.yml infra/ansible/vault/example-secrets.yml
```

- [ ] **Step 2: Update `README.md` links**

Re-point using this mapping:
- `docs/ref/arch/arch-iac.md` → `docs/explanation/4-infrastructure-as-code.md`
- `docs/ref/arch/arch-app.md` → `docs/explanation/2-application-architecture.md`
- `docs/ref/arch/README.MD` → `docs/explanation/README.md`
- `docs/ref/arch/arch-security.md` → `docs/explanation/6-security-architecture.md`
- `docs/ref/arch/arch-monitoring.md` → `docs/explanation/9-monitoring-architecture.md`
- `docs/how-to/1-install/README.md` → unchanged
- `docs/how-to/3-redeploy-guide.md` → `docs/how-to/4-redeploy.md`

- [ ] **Step 3: Update the other three files**

Apply the same mapping to any hits from Step 1 in `GEMINI.md`, `.github/release-drafter.yml`, and `infra/ansible/vault/example-secrets.yml`. If a file has no `docs/` links, leave it unchanged.

- [ ] **Step 4: Full repository link scan**

```bash
grep -rnE 'docs/ref/(arch|data|azure|workflow|project-management|troubleshooting|sys-analysis|infra)' \
  --include='*.md' --include='*.yml' --include='*.yaml' . \
  | grep -v 'docs/ref/journal' | grep -v 'docs/archive' | grep -v 'docs/superpowers'
```

Expected: no output. Any hit is a missed inbound link — fix it.

- [ ] **Step 5: Final tree and link verification**

```bash
find docs -type d | sort
scan_links
```

Expected: quadrant dirs present; `docs/ref/` contains only `journal/`; `scan_links` prints nothing.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: repoint inbound links to Diátaxis structure"
```

---

## Self-review

- **Spec coverage:** every mapping-table row in the spec appears in Tasks 1–4. The three banners are in Tasks 2 (azure-target), 3 (azure-inventory), 4 (disaster-recovery). The two consolidations are Task 2 Step 2 (troubleshoot) and Task 4 Step 2 (development-process). Inbound links are Task 6. Indexes are Tasks 2/3/4/5. Landing page is Task 5.
- **Placeholder scan:** no TBD/TODO in the plan's own steps. "Keep TODO/coming soon as-is" refers to preserving existing doc content, which is a Global Constraint (no content invention), not a plan placeholder.
- **Path consistency:** destination paths in the Interfaces blocks match the `git mv` targets and the index links in every task.
