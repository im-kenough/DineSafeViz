# Journal 35 — Code Quality Review of refresh.py and app.py

## 2026-05-07 10:00

**Task**: Review `src/dsv-db/refresh.py` and `src/dsv-app/app.py` for quality issues:
redundant state, parameter sprawl, copy-paste with variation, leaky abstractions,
stringly-typed code, unnecessary comments.

**Files read**:
- `src/dsv-db/refresh.py` (276 lines)
- `src/dsv-app/app.py` (291 lines)
- `src/dsv-db/tests/test_refresh.py` (verified context)
- `docs/ref/journal/journal-34.md` (previous session context)

**Findings**: Documented in final assistant response to the user.

---

## 2026-05-07 — Efficiency review (second pass, same session)

Reviewed the same two files for efficiency issues (hot-path bloat, redundant computation, memory, N+1 patterns, etc.). Read-only — no code changed.

Key findings:
- `inject_globals` + `index` both call `parse_year_quarter` independently on every request (double parse).
- `inject_globals` calls `get_valid_years()` a second time after `parse_year_quarter` already called it internally.
- `is_empty` uses `COUNT(*)` (full table scan) where `SELECT 1 … LIMIT 1` would short-circuit.
- `download_and_load_historical` extracts all ZIPs to disk then re-reads them; `zf.open()` would skip that round-trip.
- `_fetch_recent_rows` uses `NamedTemporaryFile(delete=False)` + manual unlink instead of a context manager.
- `build_days` always emits one entry per calendar day in the quarter (~90 entries) regardless of data density.
- No connection pool in `app.py`; each request opens a fresh TCP connection to Postgres.
