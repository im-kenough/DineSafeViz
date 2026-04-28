# Nav Consolidation Design

**Date:** 2026-04-28
**Branch:** task-header

## Goal

Move all navigation buttons (page links, inspections dropdown, social links) and page chrome (header, footer) into `base.html` so they are defined once and shared across all pages. Every page must be able to hover over the Inspections button and interact with the dropdown.

## Current State

- `base.html` is minimal: only `<head>` and `{% block body %}`
- Each of `index.html`, `dashboard.html`, `info.html` duplicates:
  - `<h1>` heading
  - `<div class="tabs">` with nav links, dropdown (index only), social links
  - `<footer>`
- The inspections dropdown only appears on `index.html`; other pages have a plain link
- Dropdown data (`year_quarters`, `selected_year`, `selected_q`) is only passed from the `/` route

## Design

### `app.py`

Move dropdown data into the `inject_globals()` context processor so it is available in all templates:

- `year_quarters`: `[(year, [quarters]), ...]` — same logic currently in `index()`
- `selected_year`: parsed from `request.args`, defaulting to current year's latest quarter
- `selected_q`: parsed from `request.args`, defaulting to latest valid quarter

Remove these three variables from the `index()` route's `render_template()` call — they will be provided by the context processor instead.

### `base.html`

New structure:

```html
<header>
  <h1>{% block heading %}DineSafeViz{% endblock %}</h1>
</header>
<nav class="tabs">
  <div class="dropdown">
    <a href="/" class="{{ 'active' if request.endpoint == 'index' else '' }}">Inspections ▾</a>
    <div class="dropdown-menu">
      {% for y, qs in year_quarters %}
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
  <a href="/dashboard" class="{{ 'active' if request.endpoint == 'dashboard' else '' }}">Dashboard</a>
  <a href="/info" class="{{ 'active' if request.endpoint == 'info' else '' }}">Info</a>
  <div class="social-links">
    <!-- LinkedIn and GitHub SVG links (unchanged) -->
  </div>
</nav>
{% block content %}{% endblock %}
<footer>
  &copy; {{ current_year }} Kenneth Ho<br>
  DineSafeViz v{{ version }}
</footer>
```

- Uses `request.endpoint` for active-tab detection (Flask exposes `request` in all templates automatically)
- No per-page logic needed for active state

### `index.html`, `dashboard.html`, `info.html`

- Remove `<h1>`, `<div class="tabs">`, and `<footer>` from each
- Rename `{% block body %}` → `{% block content %}`
- `index.html` heading block: `{% block heading %}DineSafe Inspections{% endblock %}`
- `dashboard.html` heading block: `{% block heading %}DineSafe Dashboard{% endblock %}`
- `info.html` heading block: `{% block heading %}DineSafe Information{% endblock %}`
- Child templates contain only their unique page content

### `style.css`

- No changes required. The `<nav>` element will carry `class="tabs"` so all existing `.tabs` rules apply unchanged.

## Out of Scope

- Responsive/mobile nav behaviour
- Any visual changes to the nav appearance
