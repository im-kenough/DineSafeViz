# Journal 102

## 2026-06-20 — Review src/ and update arch-app.md

### Context

User asked to review `src/` and update `docs/ref/arch/arch-app.md` to ensure
accuracy, and to include a diagram illustrating how all components interact.

### Work log

**2026-06-20 14:00** — Read src/ and cross-referenced against arch-app.md.

Discrepancies found:
- Python version: doc says `3.12`, Dockerfile says `3.14`
- Inspection sort: doc says "severity (Crucial > Significant > Minor > NA > None)" but
  code uses `STATUS_ORDER` keyed on `establishment_status` (Closed > Conditional Pass > Pass)
- "Only externally exposed" claim: dsv-analytics also has `ports: "3000:3000"` in compose
- `dinesafe_migrator` role exists in init.sql (DDL + write access) but is undocumented
- nginx explicitly returns 404 for /metrics — not mentioned in doc

**2026-06-20 14:05** — Updated arch-app.md:
- Fixed Python version to 3.14
- Corrected inspection sort description
- Noted that dsv-analytics port 3000 is also directly exposed on the host
- Added dinesafe_migrator role mention
- Added nginx /metrics block note
- Added Mermaid component interaction diagram

