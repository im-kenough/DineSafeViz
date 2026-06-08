# Journal 60

## 2026-05-11 — GitHub Projects workflow analysis

### Context
User asked for analysis of their current GitHub Projects setup and workflow improvements.
Current workflow: version-based releases (v0.1.0, v0.2.0, etc), issues with labels, parent/child issues, dependencies.
Projects to analyze: #6, #11, #12.

No changes are being made — analysis and recommendations only.

### 2026-05-11 — Backfill Start/Target dates on v0.1.0 and v0.2.0 issues

**Context:** User wants GitHub Projects Roadmap view to show historical timeline
of work. Roadmap layout requires date fields on project items.

**Actions:**
1. Created "Start date" (DATE) and "Target date" (DATE) fields on projects #6 and #11
2. Added 6 missing v0.1.0 issues (#1, #3, #4, #5, #9, #10) to project #6
3. Correlated git commit history, PR merge dates, and issue created/closed dates
4. Backfilled dates for 21 v0.1.0 issues and 6 v0.2.0 issues (54 GraphQL mutations total)

**Date strategy:**
- Start date = issue `createdAt` date (proxy for when work began)
- Target date = issue `closedAt` date (aligns with PR merge)

**Field IDs (project #6):**
- Start date: PVTF_lAHOCuXMhs4BWAc2zhSmmD0
- Target date: PVTF_lAHOCuXMhs4BWAc2zhSmmD4

**Field IDs (project #11):**
- Start date: PVTF_lAHOCuXMhs4BXSOwzhSmmD8
- Target date: PVTF_lAHOCuXMhs4BXSOwzhSmmEA

### 2026-05-11 — Create IaC verification issues for v0.3.0

**Context:** IaC code is implemented on `feat/iac-v0.3.0` but needs verification
against real Proxmox infrastructure. Created structured issues to track the work.

**Issues created:**
- #106 feat(infra): implement IaC pipeline for Proxmox homelab (parent)
  - #107 chore(infra): create Proxmox service accounts and API tokens
  - #108 chore(infra): import Ubuntu 24.04 seed image as template 9000
  - #109 feat(infra): build ubuntu-base template (9100)
  - #110 feat(infra): build ubuntu-docker template (9101)
  - #111 feat(infra): build dsv-app template (9102)
  - #112 feat(infra): provision VM with Terraform
  - #113 feat(infra): deploy app with Ansible

All added to project #6 with Start date = 2026-05-11. Target dates to be set
as each issue is closed.
