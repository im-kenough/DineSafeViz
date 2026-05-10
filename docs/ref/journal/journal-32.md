# Journal 32

## 2026-05-07 12:15 — Brainstorming: issue #64 archive sub-menu

**Task:** Fix GitHub issue #64 — bundle historic inspection years into an "Archive" sub-menu in the Inspections dropdown.

### Context gathered

- `app.py:47-53` — `get_valid_years()` returns 2001..current_year. With year 2026, that's 26 years.
- `app.py:129-143` — `inject_globals()` passes `year_quarters` (list of `(year, quarters)` tuples, newest-first) to all templates.
- `base.html:21-48` — Inspections dropdown renders all years as `.dropdown-year` divs with `.flyout` quarter links.
- `style.css:176-244` — Dropdown/flyout CSS using hover + `.is-open` class. Mobile: flyout goes `position: static`, stacks below year row.

### Issue requirement

Show last 4 years directly in the dropdown. Bundle years older than that into an "Archive" item at the bottom. Hover over Archive → years appear. Hover over year → quarters appear.

Current year is 2026, so:
- Direct: 2026, 2025, 2024, 2023
- Archive: 2022 … 2001 (22 years)

### Brainstorming in progress

Working through design with user before implementation.
