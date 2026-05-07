# Journal 36 — /simplify pass on fix-db-import branch

## 2026-05-07

**Task**: Run simplify skill — three-agent review of all code changes on the branch.

**Agents ran**: code-reuse, quality, efficiency.

**Issues found and fixed:**

### refresh.py — is_empty COUNT(*) → LIMIT 1
- `COUNT(*)` forces a full sequential scan to answer a yes/no question
- Replaced with `SELECT 1 FROM inspections LIMIT 1` which short-circuits at the first row

### refresh.py — _fetch_recent_rows TOCTOU pattern
- `NamedTemporaryFile(delete=False)` + manual `os.unlink` is fragile; file exists on disk
  unmanaged between close and unlink
- Replaced with `TemporaryDirectory`, consistent with how `download_and_load_historical` works

### refresh.py — min_inspection_date list → generator
- `[... for r in rows if ...]` allocated an intermediate list just for `min()`
- Changed to generator expression; zero-cost

### refresh.py — removed speculative comment
- "future: move to a config file" is noise; dropped

### app.py — removed WHAT comments in index()
- Four inline comments explained what the immediately following line does
- Removed all four; names are self-evident

### app.py — named magic literal 2023
- `if year == 2023: return [4]` hard-coded a data-availability fact
- Added `RECENT_DATA_START_YEAR = 2023` constant at module level

**Issues skipped:**
- Double `parse_year_quarter` call (inject_globals + index): fix requires flask.g, adds complexity
- Connection pool: architectural change, out of scope
- extractall optimization: seed-path only, correctly working
- DB config duplication across services: structural constraint
