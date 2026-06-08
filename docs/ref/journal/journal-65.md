# Journal 65

## 2026-05-12 — Update arch-app.md

### Goal

Update `docs/ref/arch/arch-app.md` to reflect the current codebase and
align with the other architecture documents.

### Research

Read all arch docs (`arch-data.md`, `arch-security.md`, `arch-ci-cd.md`,
`arch-testing.md`, `arch-iac.md`, `arch-monitoring.md`, `arch-net.md`,
`arch-dr.md`) and key source files (`docker-compose.yml`, `app.py`,
`refresh.py`, `init.sql`, `base.html`, both Dockerfiles).

### Findings

Differences between current `arch-app.md` and actual state:

- Typo in intro: "DineSaveViz" → "DineSafeViz"
- Service count wrong: doc says "five" but compose has 7 services
  (dsv-app, dsv-db, dsv-init-db, dsv-analytics, dsv-init-analytics,
  plus legacy grafana + init-grafana)
- Duplicate "Web app" headings (lines 11 and 77)
- Incomplete sentence on line 28: "Periodic updates will"
- File layout missing: static/fonts/, expanded test files, src/grafana/
- "Out of scope" lists CI/CD and testing — both now documented in
  arch-ci-cd.md and arch-testing.md
- No cross-references to other arch docs
- Data ingestion and data model sections duplicate arch-data.md content

### Changes

Rewrote arch-app.md:
- Fixed typo
- Updated service descriptions to match docker-compose.yml
- Noted legacy grafana/init-grafana services
- Consolidated duplicate Web app sections
- Updated file layout to match actual src/ tree
- Updated out-of-scope to remove items that now exist
- Added cross-references to other arch docs
- Replaced duplicated data content with pointers to arch-data.md
