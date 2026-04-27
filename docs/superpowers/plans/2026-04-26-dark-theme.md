# Dark Theme & CSS Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract inline CSS into `src/web/static/style.css`, apply a dark theme, and add severity-based row color coding via CSS classes on `<tr>`.

**Architecture:** One new static CSS file holds all styles. The template loses its `<style>` block and gains a `<link>` tag and a severity-class mapping. No Python changes.

**Tech Stack:** Flask (static file serving via `url_for`), Jinja2, plain CSS with custom properties.

---

## File Map

| Action | Path |
|--------|------|
| Create | `src/web/static/style.css` |
| Modify | `src/web/templates/index.html` |
| Modify | `src/web/tests/test_routes.py` |

---

### Task 1: Write failing test for severity class rendering

**Files:**
- Modify: `src/web/tests/test_routes.py`

- [ ] **Step 1: Append the failing test**

Add to the bottom of `src/web/tests/test_routes.py`:

```python
def test_severity_class_on_row():
    app_module.app.config["TESTING"] = True
    client = app_module.app.test_client()
    rows = [(
        date(2024, 2, 14),   # inspection_date
        "C - Crucial",       # severity
        "Court Order",       # action
        "Rats observed",     # infraction_details
        "Risky Bistro",      # establishment_name
        "1 Main St",         # establishment_address
        "Pass",              # outcome
        "2024-02-20",        # outcome_date
        "500.00",            # amount_fined
    )]
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/?year=2024&q=1")
    assert b'class="sev-crucial"' in resp.data
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd src/web && python -m pytest tests/test_routes.py::test_severity_class_on_row -v
```

Expected: `FAILED` — `AssertionError` because the current `<tr>` has no class attribute.

- [ ] **Step 3: Commit the failing test**

```bash
git add src/web/tests/test_routes.py
git commit -m "test: failing test for severity class on table row"
```

---

### Task 2: Create the stylesheet and update the template

**Files:**
- Create: `src/web/static/style.css`
- Modify: `src/web/templates/index.html`

- [ ] **Step 1: Create `src/web/static/style.css`**

Create the file with this exact content:

```css
/* ── custom properties ──────────────────────────────────── */
:root {
    --bg:              #0e1016;
    --surface:         #161920;
    --surface-2:       #1d2028;
    --border:          #262a35;
    --text:            #dde1ec;
    --text-muted:      #5e6478;
    --accent:          #4a7aff;

    --sev-crucial:     rgba(220,  38,  38, 0.6);
    --sev-significant: rgba(234,  88,  12, 0.6);
    --sev-minor:       rgba(202, 138,   4, 0.6);
    --sev-na:          rgba( 22, 163,  74, 0.6);
    --sev-none:        rgba( 37,  99, 235, 0.6);
}

/* ── base ───────────────────────────────────────────────── */
body {
    font-family: sans-serif;
    margin: 2rem;
    max-width: 1200px;
    background: var(--bg);
    color: var(--text);
}

/* ── tabs ───────────────────────────────────────────────── */
.tabs { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
.tabs a {
    padding: 0.4rem 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    text-decoration: none;
    color: var(--text-muted);
    background: var(--surface);
}
.tabs a.active {
    background: var(--surface-2);
    color: var(--text);
    border-color: var(--accent);
}
.tabs a:hover:not(.active) { background: var(--surface-2); }

/* ── day box ────────────────────────────────────────────── */
.day-box {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
    background: var(--surface);
}
.day-box h2 {
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
    font-weight: bold;
    color: var(--text-muted);
}
.no-data { margin: 0; color: var(--text-muted); font-style: italic; }

/* ── table ──────────────────────────────────────────────── */
table { border-collapse: collapse; width: 100%; }
th, td {
    border: 1px solid var(--border);
    padding: 0.35rem 0.6rem;
    text-align: left;
    font-size: 0.875rem;
}
th {
    background: var(--surface-2);
    font-weight: 600;
    white-space: nowrap;
    color: var(--text-muted);
}

/* ── severity rows ──────────────────────────────────────── */
tr.sev-crucial     { background-color: var(--sev-crucial); }
tr.sev-significant { background-color: var(--sev-significant); }
tr.sev-minor       { background-color: var(--sev-minor); }
tr.sev-na          { background-color: var(--sev-na); }
tr.sev-none        { background-color: var(--sev-none); }
```

- [ ] **Step 2: Replace `index.html` with the updated version**

Replace the entire contents of `src/web/templates/index.html` with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DineSafeViz</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <h1>DineSafe Inspections</h1>

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

    {% set sev_class = {
        'C - Crucial':     'sev-crucial',
        'S - Significant': 'sev-significant',
        'M - Minor':       'sev-minor',
        'NA':              'sev-na',
        'None':            'sev-none'
    } %}

    {% for day, rows in days %}
    <div class="day-box">
        <h2>{{ day.strftime('%A, %B %-d, %Y') }}</h2>
        {% if rows %}
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Action</th>
                    <th>Infraction Details</th>
                    <th>Establishment Name</th>
                    <th>Address</th>
                    <th>Outcome</th>
                    <th>Outcome Date</th>
                    <th>Amount Fined</th>
                </tr>
            </thead>
            <tbody>
                {% for row in rows %}
                <tr class="{{ sev_class.get(row.severity, '') }}">
                    <td>{{ row.severity or '—' }}</td>
                    <td>{{ row.action or '—' }}</td>
                    <td>{{ row.infraction_details or '—' }}</td>
                    <td>{{ row.establishment_name or '—' }}</td>
                    <td>{{ row.establishment_address or '—' }}</td>
                    <td>{{ row.outcome or '—' }}</td>
                    <td>{{ row.outcome_date or '—' }}</td>
                    <td>{{ row.amount_fined or '—' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p class="no-data">No data</p>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
```

- [ ] **Step 3: Run all tests**

```bash
cd src/web && python -m pytest tests/ -v
```

Expected: all 6 tests pass, including `test_severity_class_on_row`.

- [ ] **Step 4: Commit**

```bash
git add src/web/static/style.css src/web/templates/index.html
git commit -m "feat: dark theme with severity row colors, extract CSS to static file"
```
