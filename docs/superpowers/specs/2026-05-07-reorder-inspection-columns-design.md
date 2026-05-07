# Design: Reorder Inspection Table Columns

**Date:** 2026-05-07  
**Issue:** #73 — feat(ui): reorder the columns for clarity  
**Branch:** feat-new-cols

## Summary

Reorder and restructure the columns in the inspections table (`/inspections`) for improved readability. Merge the separate "Establishment Name" and "Address" columns into a single "Establishment" column (two lines, same styling). Add the previously-hidden "Establishment Type" column.

Note: The routing change described in the issue (point 2) — `/` as home, `/inspections` for the table — was already completed in PR #74 and requires no further work.

## Changes

### `src/web/app.py`

Add `establishment_type` to the SQL SELECT and the row dictionary in the `index()` route. No other changes.

### `src/web/templates/index.html`

Reorder `<th>` and `<td>` columns to:

| # | Header             | Rendered as                                              |
|---|--------------------|----------------------------------------------------------|
| 1 | Severity           | `row.severity`                                           |
| 2 | Infraction Details | `row.infraction_details`                                 |
| 3 | Establishment      | `row.establishment_name` + `<br>` + `row.establishment_address` |
| 4 | Establishment Type | `row.establishment_type`                                 |
| 5 | Action             | `row.action`                                             |
| 6 | Outcome            | `row.outcome`                                            |
| 7 | Outcome Date       | `row.outcome_date`                                       |
| 8 | Amount Fined       | `row.amount_fined`                                       |

The two lines in the Establishment cell use a `<br>` tag — no extra styling, matching the issue example exactly.

## Out of scope

- No changes to `home.html`, `base.html`, `dashboard.html`, or `info.html`
- No CSS changes
- No changes to the DB schema (column already exists)
