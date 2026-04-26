# Journal 1 — Architect the DineSafeViz app

## 2026-04-26 — Session start

### Context
- Branch: `4-setup-a-db`
- Goal: Design a dockerized proof-of-concept — Postgres DB loaded from CSV, simple web app showing inspection dates and violation status
- CSV: `db/Dinesafe.csv`, ~18,380 rows, 17 columns
- Existing project: docs/scaffolding only, no running code

### 2026-04-26 00:00 — Explored project state
- Read `docs/ref/data.md` — data dictionary and sample rows
- Read `db/Dinesafe.csv` header — confirmed column names match data.md
- Checked existing files: `src/tools/create_db.py` is empty, `docs/ref/arch.md` is empty
- `.gitignore` already covers Python, env files, etc.

### 2026-04-26 00:01 — Starting brainstorm for architecture
- User wants: Docker Compose with Postgres + web app containers
- User is a sysadmin, not an app dev — simplicity is paramount
- Proof of concept: load CSV into Postgres, web app displays data

### 2026-04-26 00:05 — Design decisions made
- Stack: Flask + Jinja2 templates (server-side rendering, no JS framework)
- DB loading: SQL init script via Postgres `/docker-entrypoint-initdb.d/`
- Postgres 17 (latest LTS), Python 3.12-slim (latest LTS)
- Single table `inspections` mapping CSV columns (skip `_id`, use own SERIAL PK)
- Single route `/` showing date, establishment, violations yes/no
- Spec written to `docs/superpowers/specs/2026-04-26-poc-design.md`
