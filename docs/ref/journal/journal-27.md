# Journal 27 — Data Ingestion Refactor

**Plan:** `docs/superpowers/plans/2026-05-07-data-ingestion.md`
**Spec:** `docs/superpowers/specs/2026-05-07-data-ingestion-design.md`

---

## 2026-05-07 — Tasks 1–8: Full data ingestion refactor executed

All 8 tasks completed. Commits:

1. `refactor: make init.sql schema-only, add historical columns` — removed staging table, COPY, INSERT, DROP; added 2 new columns
2. `feat: add refresh.py config, normalize, and column mapping` — TDD, 16 tests green
3. `feat: add DB connection, is_empty, and bulk_insert to refresh.py` — psycopg2 COPY-based bulk insert
4. `feat: add seed path — download historical ZIP + recent CSV`
5. `feat: add daily refresh path and CLI entrypoint to refresh.py`
6. `feat: extend data range to 2001-present` — updated DATA_START, get_valid_years(), fixed 2 tests
7. `chore: remove static CSV volume mount from db service`
8. `docs: add unified schema and ingestion workflow to data.md`

Final: 16 db tests + 44 web tests all pass.
