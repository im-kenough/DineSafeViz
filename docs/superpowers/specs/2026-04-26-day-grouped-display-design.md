# Day-Grouped Inspection Display — Design Spec

**Date:** 2026-04-26
**Branch:** dev-app

## Overview

Replace the current flat inspection table with a day-grouped layout. Each calendar day from 2023-11-09 to the current date gets its own rounded box. Navigation is by year tab and quarter sub-tab. This is a pure server-side change to `app.py` and `index.html`.

## Navigation

Two-level navigation rendered as tab-style links:

- **Year tabs**: 2023, 2024, 2025, 2026
- **Quarter sub-tabs**: Q1, Q2, Q3, Q4 (only quarters within the data range)

URL structure: `/?year=2026&q=2`

Default (no params): most recent year and most recent completed/current quarter.

**Valid quarter bounds:**
- 2023: Q4 only (data starts 2023-11-09)
- 2024, 2025: Q1–Q4
- 2026: Q1–Q2 (data ends at current date)

Invalid or out-of-range params redirect to the default.

## Day Boxes

The main content area lists one box per calendar day in the selected quarter, newest first.

**Day with data:**
```
┌──────────────────────────────────────────────────────────┐
│ Saturday, April 26, 2026                                 │
│                                                          │
│ Severity | Action | Infraction Details | Establishment   │
│          |        |                    | Name | Address  │
│          |        |                    | Outcome |        │
│          |        |                    | Outcome Date |  │
│          |        |                    | Amount Fined    │
│ ──────────────────────────────────────────────────────── │
│ Crucial  | ...    | ...                | ...             │
│ Minor    | ...    | ...                | ...             │
└──────────────────────────────────────────────────────────┘
```

**Day with no data:**
```
┌──────────────────────────────────────────────────────────┐
│ Friday, April 25, 2026                                   │
│                                                          │
│ No data                                                  │
└──────────────────────────────────────────────────────────┘
```

No-data days are always shown (not hidden), preserving the calendar feel.

## Mini-Table Columns

Within each day box, a table with the following columns (in order):

1. Severity
2. Action
3. Infraction Details
4. Establishment Name
5. Address
6. Outcome
7. Outcome Date
8. Amount Fined

## Row Sort Order

Rows within a day's mini-table are sorted by severity. The actual values in the data are:

1. `C - Crucial`
2. `S - Significant`
3. `M - Minor`
4. `NA` / null (last)

Note: the user described this tier as "crucial, severe, minor" but the data uses "Significant" for the middle tier.

## Flask Implementation

### `app.py` changes

- Read `year` and `q` query params; default to current year/quarter
- Compute the date range for the selected quarter (clipped to 2023-11-09 at the start and today at the end)
- Query: `SELECT severity, action, infraction_details, establishment_name, establishment_address, outcome, outcome_date, amount_fined, inspection_date FROM inspections WHERE inspection_date BETWEEN %s AND %s ORDER BY inspection_date DESC`
- Build a dict keyed by date for O(1) day lookup in the template
- Pass to template: `days` (ordered list of dates in the quarter, newest first), `data` (dict of date → sorted list of row dicts), `years`, `quarters`, `selected_year`, `selected_q`

### `index.html` changes

- Replace flat table with day-box layout
- Year tabs and quarter sub-tabs rendered as `<a>` links with active state
- Loop over `days`; for each day render a box with either the mini-table or "No data"
- CSS: rounded border on day boxes, simple table styling inside

## Files Changed

| File | Change |
|---|---|
| `src/web/app.py` | New query, param parsing, day-map construction |
| `src/web/templates/index.html` | Full replacement of body content |

No new files, no new endpoints, no JavaScript.
