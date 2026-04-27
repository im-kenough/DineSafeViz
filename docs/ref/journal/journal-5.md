# Journal 5

## 2026-04-26 14:00 — Brainstorm: day-grouped inspection display

### Context
- Branch: `dev-app`
- Current app: flat table with 3 columns (date, establishment, violation)
- User wants a new layout: one rounded box per day, year+quarter navigation

### Session goal
Design and spec a day-grouped display for the DineSafe inspection data.

### Design decisions
- **Navigation**: year tabs (2023–2026) + quarter sub-tabs (Q1–Q4), URL params `?year=&q=`
- **Default**: most recent year + quarter
- **Edge cases**: 2023 shows only Q4 (data starts Nov 9); 2026 shows only Q1+Q2 (data ends today)
- **Day boxes**: every calendar day in the quarter gets a box, newest-first
- **No data days**: box still shown, displays "No data"
- **Mini-table columns**: Severity, Action, Infraction Details, Establishment Name, Address, Outcome, Outcome Date, Amount Fined
- **Row sort within day**: Crucial → Significant → Minor → null
- **Implementation**: server-side Flask only, URL params, no JS, no new endpoints

### Files to change
- `src/web/app.py` — read year/q params, query by date range, build day-map
- `src/web/templates/index.html` — replace flat table with day-box layout
