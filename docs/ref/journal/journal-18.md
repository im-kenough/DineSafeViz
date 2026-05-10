# Journal 18

## 2026-04-28 — /simplify review of task-header branch changes

Running `/simplify` on `src/dsv-app/` to review changes on the `task-header` branch vs `main`.

### Changes in scope (main...HEAD diff)
- `app.py`: Added `get_version()`, `inject_globals()` context processor, `/dashboard`, `/info` routes, Grafana reverse-proxy
- `style.css`: Added header, page-heading, footer, social-links, dropdown/flyout CSS
- `base.html`: New base template (header, nav with year/quarter dropdown, social links, footer)
- `dashboard.html`, `info.html`: New pages extending base.html
- `index.html`: Refactored to extend base.html
- `tests/test_routes.py`: Refactored to fixture pattern, added new tests
- `tests/test_grafana_proxy.py`: New file with Grafana proxy tests
- `VERSION.txt`, favicon assets, `requirements.txt`: Supporting files

### Review agents launched
Three agents running in parallel: code reuse, quality, efficiency.

## 2026-04-28 — Fixes applied

### 1. Cache `get_version()` at module load (`app.py`)
Renamed to `_read_version()`, called once at module level into `_VERSION`. Previously called on every request via context processor.

### 2. Rename `excluded_headers` → `_hop_by_hop` (`app.py`)
Self-documenting name (RFC 2616 §13.5.1 hop-by-hop headers), no comment needed.

### 3. Use `url_for` in nav links (`base.html`)
Replaced hardcoded `/`, `/dashboard`, `/info` with `url_for('index')`, `url_for('dashboard')`, `url_for('info')`. For flyout links with query params, added `| safe` to prevent `&` being HTML-escaped to `&amp;`.

### 4. Extract `.nav-btn` CSS utility class (`style.css`, `base.html`)
Eliminated triple copy-paste of 7 identical declarations across `.tabs > a`, `.social-links a`, `.flyout a`, `.dropdown-year`. Now all shared styles live in `.nav-btn`.

### Pre-existing test bug fixed
`test_info_page` asserted `b"DineSafe Information"` but the page heading is "DineSafeViz Info". Fixed assertion to match actual content.

### Tests: 44 passed, 0 failed
