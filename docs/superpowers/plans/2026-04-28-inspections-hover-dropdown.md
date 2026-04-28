# Inspections Hover Dropdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the year/quarter tab rows on the Inspections page with a two-level CSS hover dropdown on the "Inspections" nav button.

**Architecture:** The "Inspections" nav link becomes a hover-triggered dropdown listing years (descending); hovering a year reveals its valid quarters in a flyout to the right. Pure CSS — no JavaScript. Backend passes a pre-sorted list of `(year, quarters)` tuples so the template can iterate without sorting logic.

**Tech Stack:** Flask/Jinja2, CSS, pytest

---

## File Map

| File | Change |
|------|--------|
| `src/web/app.py` | Replace `valid_years` + `valid_quarters` kwargs with `year_quarters` list of tuples |
| `src/web/templates/index.html` | Replace two `.tabs` rows with `.dropdown` HTML; iterate `year_quarters` |
| `src/web/static/style.css` | Add `.dropdown`, `.dropdown-menu`, `.dropdown-year`, `.flyout` rules |
| `src/web/tests/test_routes.py` | Add tests for dropdown HTML structure; update removed-tabs assertion |

---

### Task 1: Write failing tests for the new dropdown structure

**Files:**
- Modify: `src/web/tests/test_routes.py`

- [ ] **Step 1: Add three new tests to `test_routes.py`**

Append to the end of `src/web/tests/test_routes.py`:

```python
def test_dropdown_menu_present(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_year_and_quarter_links(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    # 2023 only has Q4
    assert b'href="/?year=2023&q=4"' in resp.data
    assert b'href="/?year=2023&q=1"' not in resp.data
    # 2024 has all four quarters
    assert b'href="/?year=2024&q=1"' in resp.data
    assert b'href="/?year=2024&q=4"' in resp.data


def test_standalone_year_tabs_removed(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    # Old year-only tab links (no &q= param) must be gone
    assert b'href="/?year=2024"' not in resp.data
    assert b'href="/?year=2023"' not in resp.data
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
cd src/web && python3 -m pytest tests/test_routes.py::test_dropdown_menu_present tests/test_routes.py::test_dropdown_has_year_and_quarter_links tests/test_routes.py::test_standalone_year_tabs_removed -v
```

Expected: all three FAIL (template not updated yet).

---

### Task 2: Update `app.py` — pass `year_quarters` instead of `valid_years`/`valid_quarters`

**Files:**
- Modify: `src/web/app.py:238-246`

- [ ] **Step 1: Replace the two kwargs in the `render_template` call in the `/` route**

In `src/web/app.py`, find the `render_template` call in `index()` (around line 239). Replace:

```python
    return render_template(
        "index.html",
        days=build_days(rows, start, end),
        selected_year=year,
        selected_q=q,
        valid_years=get_valid_years(),
        valid_quarters=get_valid_quarters(year),
    )
```

With:

```python
    return render_template(
        "index.html",
        days=build_days(rows, start, end),
        selected_year=year,
        selected_q=q,
        year_quarters=[(y, get_valid_quarters(y)) for y in sorted(get_valid_years(), reverse=True)],
    )
```

- [ ] **Step 2: Run all existing tests to confirm nothing is broken**

```bash
cd src/web && python3 -m pytest tests/ -q
```

Expected: the three new tests still FAIL (template not updated yet), but all 34 pre-existing tests PASS. Total: 34 passed, 3 failed.

---

### Task 3: Update `index.html` — replace year/quarter tabs with dropdown

**Files:**
- Modify: `src/web/templates/index.html`

- [ ] **Step 1: Replace the nav + year/quarter tabs section**

In `src/web/templates/index.html`, replace lines 6–24:

```html
    <div class="tabs">
        <a href="/" class="active">Inspections</a>
        <a href="/dashboard">Dashboard</a>
        <a href="/info">Info</a>
    </div>

    <div class="tabs">
        {% for y in valid_years %}
        <a href="/?year={{ y }}"
           class="{{ 'active' if y == selected_year else '' }}">{{ y }}</a>
        {% endfor %}
    </div>

    <div class="tabs">
        {% for q in valid_quarters %}
        <a href="/?year={{ selected_year }}&q={{ q }}"
           class="{{ 'active' if q == selected_q else '' }}">Q{{ q }}</a>
        {% endfor %}
    </div>
```

With:

```html
    <div class="tabs">
        <div class="dropdown">
            <a href="/" class="active">Inspections ▾</a>
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
        <a href="/dashboard">Dashboard</a>
        <a href="/info">Info</a>
    </div>
```

- [ ] **Step 2: Run the three new tests to confirm they now pass**

```bash
cd src/web && python3 -m pytest tests/test_routes.py::test_dropdown_menu_present tests/test_routes.py::test_dropdown_has_year_and_quarter_links tests/test_routes.py::test_standalone_year_tabs_removed -v
```

Expected: all three PASS.

- [ ] **Step 3: Run the full test suite**

```bash
cd src/web && python3 -m pytest tests/ -q
```

Expected: 37 passed, 0 failed.

- [ ] **Step 4: Commit**

```bash
git add src/web/app.py src/web/templates/index.html src/web/tests/test_routes.py
git commit -m "feat: replace year/quarter tabs with hover dropdown on Inspections button"
```

---

### Task 4: Add CSS for dropdown and flyout

**Files:**
- Modify: `src/web/static/style.css`

- [ ] **Step 1: Append dropdown CSS to `src/web/static/style.css`**

Append after the `footer` block (after line 91):

```css
/* ── inspections dropdown ───────────────────────────────── */
.dropdown { position: relative; display: inline-block; }

.dropdown-menu {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    z-index: 10;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    min-width: 90px;
    padding: 0.25rem 0;
}
.dropdown:hover .dropdown-menu { display: block; }

.dropdown-year {
    position: relative;
    padding: 0.4rem 2rem 0.4rem 1rem;
    color: var(--text-muted);
    white-space: nowrap;
    cursor: default;
}
.dropdown-year:hover { background: var(--surface-2); color: var(--text); }

.flyout {
    display: none;
    position: absolute;
    left: 100%;
    top: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.25rem;
    flex-direction: column;
    gap: 0.25rem;
}
.dropdown-year:hover .flyout { display: flex; }

.flyout a {
    padding: 0.4rem 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    text-decoration: none;
    color: var(--text-muted);
    background: var(--surface);
    white-space: nowrap;
}
.flyout a.active {
    background: var(--surface-2);
    color: var(--text);
    border-color: var(--accent);
}
.flyout a:hover:not(.active) { background: var(--surface-2); }
```

- [ ] **Step 2: Run the full test suite to confirm nothing broke**

```bash
cd src/web && python3 -m pytest tests/ -q
```

Expected: 37 passed, 0 failed.

- [ ] **Step 3: Commit**

```bash
git add src/web/static/style.css
git commit -m "style: add CSS for inspections hover dropdown and quarter flyout"
```
