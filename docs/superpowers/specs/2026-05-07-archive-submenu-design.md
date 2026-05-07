# Archive Sub-Menu Design

**Issue:** #64  
**Branch:** fix-archive-yrs  
**Date:** 2026-05-07

## Overview

The Inspections dropdown currently lists all years (2001–present) as a flat list. With 26+ years, this grows unwieldy. This change shows only the 4 most recent years directly and bundles the rest into an "Archive" sub-menu at the bottom.

## Behaviour

- Inspections dropdown shows: current year + 3 prior years, then "Archive ›" at the bottom.
- Hovering/clicking Archive reveals the older years as a flyout.
- Hovering/clicking a year in the Archive flyout reveals its quarters, same as today.
- On desktop: hover opens flyouts, cascading right.
- On mobile: click/tap toggles flyouts inline (same pattern as today, works at all nesting depths).

## Changes

### `app.py`

- Add constant `RECENT_YEARS = 4` (module-level).
- In `inject_globals()`, split `year_quarters` into two lists:
  - `recent_year_quarters` — first `RECENT_YEARS` entries (already sorted newest-first).
  - `archive_year_quarters` — the remainder (older years, also newest-first within the group).
- Remove `year_quarters` from the context dict; replace with the two new keys.

### `base.html`

- Loop `recent_year_quarters` exactly as today (`.dropdown-year` + `.flyout` with quarter links).
- Below that, if `archive_year_quarters` is non-empty, render one Archive `.dropdown-year` item.
  - Its `.flyout` contains the archive year items, each a `.dropdown-year` with a quarter flyout — identical structure to the recent years.

### `style.css`

- Add a top border or margin separator above the Archive item to visually distinguish it from the recent years.
- No new classes needed; existing `.dropdown-year` / `.flyout` pattern works at any nesting depth.

### JS (inline in `base.html`)

- Change the click-handler selector from `.dropdown-menu > .dropdown-year` to `.dropdown-year` (all depths), so the tap-to-toggle behaviour works inside the Archive flyout too.
- **Sibling-close must be scoped to the immediate parent container.** The current code closes all `.flyout.is-open` within `.dropdown-menu` — this would accidentally close the Archive flyout when tapping a year inside it. Fix: when toggling a `.dropdown-year`, close only the open flyouts whose `.dropdown-year` parent is a sibling of the clicked item (i.e., query from `yr.parentElement`, not from `menu`).

## Not in scope

- Changing the number of recent years (4) at runtime.
- Any changes to how quarters are displayed or queried.
- Modifying tests beyond what the `inject_globals` change requires.
