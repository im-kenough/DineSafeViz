# Archive Sub-Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bundle inspection years older than the 4 most recent into a nested "Archive" flyout at the bottom of the Inspections dropdown.

**Architecture:** Split `year_quarters` in `inject_globals()` into `recent_year_quarters` (last 4 years) and `archive_year_quarters` (the rest). Update `base.html` to render Archive as a third-level flyout using the same `.dropdown-year` / `.flyout` HTML pattern that already exists. Fix the JS sibling-close to scope to the immediate parent rather than the entire menu, so opening a year inside Archive doesn't close Archive itself.

**Tech Stack:** Python/Flask (Jinja2), vanilla JS, plain CSS.

---

### Task 1: Write failing tests

**Files:**
- Modify: `src/web/tests/test_routes.py`

- [ ] **Step 1: Add three failing tests to `test_routes.py`**

Append to the bottom of `src/web/tests/test_routes.py`:

```python
def test_dropdown_has_archive_item(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'archive-item' in resp.data
    assert b'Archive' in resp.data


def test_archive_contains_old_year_links(client):
    # 2022 is older than the 4 most recent years (2026,2025,2024,2023)
    # and should still appear in the response (inside the archive flyout)
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'href="/?year=2022&q=1"' in resp.data


def test_recent_years_not_in_archive(client):
    # year_quarters (the old combined key) must be gone from context;
    # the template renders without it. Also confirms 2023 still renders.
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'href="/?year=2023&amp;q=4"' in resp.data
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```bash
cd src/web && python -m pytest tests/test_routes.py::test_dropdown_has_archive_item tests/test_routes.py::test_archive_contains_old_year_links tests/test_routes.py::test_recent_years_not_in_archive -v
```

Expected: all three FAIL (archive-item class and Archive text not yet rendered).

---

### Task 2: Update `app.py` — split year list

**Files:**
- Modify: `src/web/app.py`

- [ ] **Step 1: Add `RECENT_YEARS` constant after `SEVERITY_ORDER`**

In `src/web/app.py`, after line 25 (`}`), add:

```python
RECENT_YEARS = 4
```

- [ ] **Step 2: Replace `year_quarters` with split lists in `inject_globals()`**

Replace the entire `inject_globals` function (lines 129–143) with:

```python
@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    year, q = parse_year_quarter(request.args)
    years = get_valid_years()
    year_quarters = [
        (y, get_valid_quarters(y))
        for y in sorted(years, reverse=True)
    ]
    return {
        "current_year": date.today().year,
        "version": _VERSION,
        "recent_year_quarters": year_quarters[:RECENT_YEARS],
        "archive_year_quarters": year_quarters[RECENT_YEARS:],
        "selected_year": year,
        "selected_q": q,
    }
```

- [ ] **Step 3: Run the full test suite to confirm only the new tests still fail (no regressions)**

```bash
cd src/web && python -m pytest tests/ -v
```

Expected: existing tests pass; the three new tests still fail because the template hasn't been updated yet.

---

### Task 3: Update `base.html` — render Archive in dropdown

**Files:**
- Modify: `src/web/templates/base.html`

- [ ] **Step 1: Replace the dropdown-menu block (lines 21–35)**

Replace:

```html
        <div class="dropdown">
            <a href="{{ url_for('index') }}" class="nav-btn {{ 'active' if request.endpoint == 'index' else '' }}">Inspections ▾</a>
            <div class="dropdown-menu">
                {% for y, qs in year_quarters %}
                <div class="nav-btn dropdown-year">
                    <span>{{ y }} ›</span>
                    <div class="flyout">
                        {% for q in qs %}
                        <a href="{{ url_for('index', year=y, q=q) | safe }}"
                           class="nav-btn {{ 'active' if y == selected_year and q == selected_q else '' }}">Q{{ q }}</a>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
```

With:

```html
        <div class="dropdown">
            <a href="{{ url_for('index') }}" class="nav-btn {{ 'active' if request.endpoint == 'index' else '' }}">Inspections ▾</a>
            <div class="dropdown-menu">
                {% for y, qs in recent_year_quarters %}
                <div class="nav-btn dropdown-year">
                    <span>{{ y }} ›</span>
                    <div class="flyout">
                        {% for q in qs %}
                        <a href="{{ url_for('index', year=y, q=q) | safe }}"
                           class="nav-btn {{ 'active' if y == selected_year and q == selected_q else '' }}">Q{{ q }}</a>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
                {% if archive_year_quarters %}
                <div class="nav-btn dropdown-year archive-item">
                    <span>Archive ›</span>
                    <div class="flyout">
                        {% for y, qs in archive_year_quarters %}
                        <div class="nav-btn dropdown-year">
                            <span>{{ y }} ›</span>
                            <div class="flyout">
                                {% for q in qs %}
                                <a href="{{ url_for('index', year=y, q=q) | safe }}"
                                   class="nav-btn {{ 'active' if y == selected_year and q == selected_q else '' }}">Q{{ q }}</a>
                                {% endfor %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
```

- [ ] **Step 2: Run the new tests**

```bash
cd src/web && python -m pytest tests/test_routes.py::test_dropdown_has_archive_item tests/test_routes.py::test_archive_contains_old_year_links tests/test_routes.py::test_recent_years_not_in_archive -v
```

Expected: all three PASS.

- [ ] **Step 3: Run the full test suite**

```bash
cd src/web && python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add src/web/app.py src/web/templates/base.html src/web/tests/test_routes.py
git commit -m "feat(ui): add Archive sub-menu for historic inspection years"
```

---

### Task 4: Fix JS sibling-close scope

**Files:**
- Modify: `src/web/templates/base.html`

- [ ] **Step 1: Replace the JS block (lines 51–93)**

Replace the entire `<script>` block with:

```html
    <script>
    (function () {
        var dropdown = document.querySelector('.dropdown');
        if (!dropdown) return;
        var menu = dropdown.querySelector('.dropdown-menu');
        var trigger = dropdown.querySelector('a.nav-btn');

        // Toggle top-level dropdown; prevent the trigger link from navigating
        trigger.addEventListener('click', function (e) {
            e.preventDefault();
            var opening = menu.classList.toggle('is-open');
            if (opening) {
                menu.querySelectorAll('.flyout.is-open').forEach(function (f) {
                    f.classList.remove('is-open');
                });
            }
        });

        // Toggle year/archive flyouts at any nesting depth.
        // Sibling-close is scoped to the immediate parent so that opening a year
        // inside Archive does not accidentally close the Archive flyout itself.
        menu.querySelectorAll('.dropdown-year').forEach(function (yr) {
            yr.addEventListener('click', function (e) {
                if (e.target.closest('a')) return;
                e.stopPropagation();
                var flyout = yr.querySelector('.flyout');
                var opening = !flyout.classList.contains('is-open');
                yr.parentElement.querySelectorAll(':scope > .dropdown-year > .flyout.is-open').forEach(function (f) {
                    f.classList.remove('is-open');
                });
                if (opening) flyout.classList.add('is-open');
            });
        });

        // Close everything on outside click
        document.addEventListener('click', function (e) {
            if (!dropdown.contains(e.target)) {
                menu.classList.remove('is-open');
                menu.querySelectorAll('.flyout.is-open').forEach(function (f) {
                    f.classList.remove('is-open');
                });
            }
        });
    }());
    </script>
```

- [ ] **Step 2: Run the full test suite**

```bash
cd src/web && python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/web/templates/base.html
git commit -m "fix(ui): scope sibling-close to parent so Archive stays open"
```

---

### Task 5: Add CSS separator above Archive item

**Files:**
- Modify: `src/web/static/style.css`

- [ ] **Step 1: Add `.archive-item` rule in the inspections dropdown section**

In `src/web/static/style.css`, after the `.flyout a { display: block; }` line (line 221), add:

```css
.archive-item {
    border-top: 1px solid var(--border);
    margin-top: 0.25rem;
}
```

- [ ] **Step 2: Run the full test suite**

```bash
cd src/web && python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/web/static/style.css
git commit -m "style(ui): add separator above Archive item in inspections dropdown"
```
