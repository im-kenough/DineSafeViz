# Journal 17

## 2026-04-28 — Fix centered DineSafeViz header on all pages

### Context
Branch: `task-header`
Task: "DineSafeViz" should be a centered header visible on all pages.

### Analysis
- `base.html` had `<h1>{% block heading %}DineSafeViz{% endblock %}</h1>`
- Every child template overrode that block:
  - `index.html`: "DineSafe Inspections"
  - `dashboard.html`: "DineSafe Dashboard"
  - `info.html`: "DineSafe Information"
- Result: "DineSafeViz" was never shown on any page.
- Additionally, no CSS existed for `header` — no centering, no margin.

### Changes made
- `base.html`: hardcoded `<h1>DineSafeViz</h1>` (removed block override), dropped `{% block heading %}` entirely
- `style.css`: added `header` and `header h1` rules for centering and accent color
- `index.html`, `dashboard.html`, `info.html`: removed orphaned `{% block heading %}` blocks

## 2026-04-28 — Add left-justified page-level headings

- Added `<h2 class="page-heading">` at top of `{% block content %}` in each page:
  - `index.html`: "DineSafe Inspections"
  - `dashboard.html`: "DineSafe Dashboard"
  - `info.html`: "DineSafeViz Info"
- Added `h2.page-heading` CSS rule (1.5rem, bold, `var(--text)`, left-aligned)
