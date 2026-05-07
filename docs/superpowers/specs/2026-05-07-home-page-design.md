# Home Page Design — Issue #63

**Date:** 2026-05-07
**Issue:** feat(ui): add a home page (#63)
**Milestone:** v0.2.0

## Summary

Add a home page at `/`, move the Inspections page to `/inspections`, make the H1 link to home, and add a Home button as the leftmost nav item.

## Route Changes

| Route | Handler | Before | After |
|---|---|---|---|
| `/` | `home()` | — | New home page |
| `/inspections` | `index()` | `/` | Moved |

The `index` function keeps its name. Only the `@app.route` decorator path changes from `"/"` to `"/inspections"`. All `url_for('index')` calls in templates continue to work without modification.

## Home Page Layout (`home.html`)

Extends `base.html`. Three sections, top to bottom:

1. **Hero** — centered, contains:
   - A tagline sub-heading (e.g. "Toronto Food Safety Inspections")
   - One sentence describing the site ("25+ years of DineSafe inspection data from Toronto Public Health, visualized.")

2. **Stat strip** — two side-by-side cards:
   - "Years of Data" — dynamic integer derived from `max_year - min_year + 1`
   - "Total Inspections" — dynamic integer from `COUNT(*)`
   - Cards styled with existing `.day-box` CSS; numbers rendered in large accent-colored (`var(--accent)`) font

3. **Nav cards** — three cards in a row linking to:
   - Inspections (`url_for('index')`)
   - Dashboard (`url_for('dashboard')`)
   - Info (`url_for('info')`)
   - Each card has a title and a one-line description

All page-specific CSS lives in a `{% block head %}<style>...</style>{% endblock %}` block, matching the pattern used in `info.html` and `dashboard.html`. No new CSS variables are introduced.

## Stats Caching (`app.py`)

A module-level dict `_stats_cache` holds cached values:

```python
_stats_cache = {"data": None, "fetched_at": None}
TTL = timedelta(days=5)
```

On each home page request:
- If `_stats_cache["data"]` is `None` or `datetime.now() - _stats_cache["fetched_at"] > TTL`, run two queries:
  1. `SELECT COUNT(*) FROM inspections` → `total_inspections`
  2. `SELECT MIN(inspection_date), MAX(inspection_date) FROM inspections` → `years_of_data = max_year - min_year + 1`
- Store results and `datetime.now()` in `_stats_cache`
- Pass stats to `render_template("home.html", ...)`

TTL is 5 days — appropriate since the DB refreshes at most daily.

## Nav Changes (`base.html`)

1. **H1 becomes a link:**
   ```html
   <a href="{{ url_for('home') }}"><h1>DineSafeViz</h1></a>
   ```

2. **Home button added as the leftmost nav item** (before the Inspections dropdown):
   ```html
   <a href="{{ url_for('home') }}" class="nav-btn {{ 'active' if request.endpoint == 'home' else '' }}">Home</a>
   ```

## Files Changed

| File | Change |
|---|---|
| `src/web/app.py` | Add `home()` route at `/`; change `index()` route to `/inspections`; add `_stats_cache` and TTL logic |
| `src/web/templates/base.html` | H1 → link; add Home nav button |
| `src/web/templates/home.html` | New file |

## Out of Scope

- No changes to Dashboard, Info, or Inspections page content
- No new Python packages
- No changes to existing CSS variables or `style.css`
