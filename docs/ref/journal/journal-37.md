# Journal 37

## 2026-05-07 — Code review: home page changes for reuse opportunities

Task: Review diff of home page changes (app.py, templates, tests) for code reuse opportunities against existing patterns in the codebase.

Read full app.py at /home/sam/SCM/github/DineSafeViz/src/web/app.py to assess:
1. Whether `_get_home_stats()` duplicates existing DB connection/query patterns
2. Whether a caching utility already exists
3. Whether the two-query approach duplicates existing data-fetch patterns

### Findings

**DB connection pattern** — `index()` (lines 259–284) opens a connection with `psycopg2.connect(**DB_CONFIG)`, runs queries, then calls `cur.close()` / `conn.close()`. `_get_home_stats()` (lines 215–225) does the exact same thing. No shared helper exists; both inline the open/close manually.

**Caching** — No prior caching mechanism exists in the file. `_stats_cache` / `_STATS_TTL` are entirely new.

**Two-query pattern** — `index()` runs one query with a WHERE clause. `_get_home_stats()` runs two separate single-stat queries. No duplicate of that specific pattern exists.

Reporting findings as text response.
