# Inspections Hover Dropdown Design

**Date:** 2026-04-28  
**Branch:** task-ui-hover-btn

## Summary

Replace the existing year and quarter tab rows on the Inspections page with a two-level CSS hover dropdown on the "Inspections" nav button. Hovering "Inspections" reveals years in descending order; hovering a year reveals its valid quarters in a flyout to the right.

## Motivation

The three stacked tab rows (nav / year / quarter) are verbose. Collapsing year and quarter selection into a hover dropdown reduces visual noise while keeping all navigation accessible.

## Scope

- `src/web/templates/index.html` — replace year/quarter tab rows with dropdown HTML
- `src/web/static/style.css` — add dropdown and flyout CSS
- `src/web/app.py` — replace `valid_years` + `valid_quarters` with `year_quarters` dict

**Out of scope:** Dashboard and Info pages are unchanged.

## HTML Structure

The "Inspections" nav item in `index.html` becomes a `<div class="dropdown">` wrapper:

```html
<div class="dropdown">
  <a href="/" class="active">Inspections ▾</a>
  <div class="dropdown-menu">
    {% for y, qs in year_quarters.items() | sort(reverse=True) %}
    <div class="dropdown-year">
      <span>{{ y }} ›</span>
      <div class="flyout">
        {% for q in qs %}
        <a href="/?year={{ y }}&q={{ q }}"
           class="{{ 'active' if y == selected_year and q == selected_q else '' }}">Q{{ q }}</a>
        {% endfor %}
      </div>
    </div>
    {% endfor %}
  </div>
</div>
```

The two existing `.tabs` rows for year and quarter are removed.

## CSS

New rules added to `style.css`:

- `.dropdown` — `position: relative; display: inline-block`
- `.dropdown-menu` — `display: none; position: absolute; top: 100%; left: 0; z-index: 10; background: var(--surface); border: 1px solid var(--border); border-radius: 4px; min-width: 100px`
- `.dropdown:hover .dropdown-menu` — `display: block`
- `.dropdown-year` — `position: relative; padding: 0.4rem 1.5rem 0.4rem 1rem; cursor: default; color: var(--text-muted); white-space: nowrap`
- `.dropdown-year:hover` — `background: var(--surface-2); color: var(--text)`
- `.flyout` — `display: none; position: absolute; left: 100%; top: 0; background: var(--surface); border: 1px solid var(--border); border-radius: 4px; padding: 0.25rem; display: flex; flex-direction: column; gap: 0.25rem`  
  *(hidden via `.dropdown-year .flyout { display: none }`)*
- `.dropdown-year:hover .flyout` — `display: flex`
- Flyout `a` links — same styling as existing `.tabs a`

The right padding on `.dropdown-year` (via `padding-right: 1.5rem`) extends the hover target slightly into the gap between the year label and the flyout, preventing accidental dismissal on diagonal mouse movement.

## Backend Change

In `src/web/app.py`, the `/` route currently passes:

```python
valid_years=get_valid_years(),
valid_quarters=get_valid_quarters(year),
```

Replace with:

```python
year_quarters={y: get_valid_quarters(y) for y in get_valid_years()},
```

`selected_year` and `selected_q` remain as-is (needed to mark the active quarter link).

## Removed

- `valid_years` template variable
- `valid_quarters` template variable
- The year `.tabs` row in `index.html`
- The quarter `.tabs` row in `index.html`
