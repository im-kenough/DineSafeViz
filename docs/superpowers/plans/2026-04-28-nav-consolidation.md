# Nav Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all nav buttons, header, and footer into `base.html` so they are defined once and the inspections dropdown is available on every page.

**Architecture:** `inject_globals()` in `app.py` is promoted to supply dropdown navigation data to all templates. `base.html` gains a `<header>`, `<nav class="tabs">` (with full dropdown), and `<footer>`. Child templates drop those elements and expose only their unique content via `{% block content %}`.

**Tech Stack:** Flask, Jinja2, Python 3, pytest

---

## Files

| File | Change |
|------|--------|
| `src/web/app.py` | Add `year_quarters`, `selected_year`, `selected_q` to `inject_globals()`; remove them from `index()` |
| `src/web/templates/base.html` | Add `<header>`, `<nav class="tabs">` with full dropdown + social links, `<footer>`, `{% block content %}` |
| `src/web/templates/index.html` | Remove `<h1>`, `<div class="tabs">`, `<footer>`; rename block to `content`; add `{% block heading %}` |
| `src/web/templates/dashboard.html` | Same removals + rename block |
| `src/web/templates/info.html` | Same removals + rename block |
| `src/web/tests/test_routes.py` | Add tests: dropdown present on `/dashboard` and `/info`; active class per page |

---

### Task 1: Write failing tests

**Files:**
- Modify: `src/web/tests/test_routes.py`

- [ ] **Step 1: Add tests to `test_routes.py`**

Append these test functions to the end of `src/web/tests/test_routes.py`:

```python
def test_dropdown_present_on_dashboard(client):
    resp = client.get("/dashboard")
    assert b'class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_links_on_dashboard(client):
    resp = client.get("/dashboard")
    assert b'href="/?year=2023&amp;q=4"' in resp.data
    assert b'href="/?year=2024&amp;q=1"' in resp.data


def test_dropdown_present_on_info(client):
    resp = client.get("/info")
    assert b'class="dropdown"' in resp.data
    assert b'class="dropdown-menu"' in resp.data


def test_dropdown_has_links_on_info(client):
    resp = client.get("/info")
    assert b'href="/?year=2023&amp;q=4"' in resp.data
    assert b'href="/?year=2024&amp;q=1"' in resp.data


def test_dashboard_nav_active_class(client):
    resp = client.get("/dashboard")
    assert b'href="/dashboard" class="active"' in resp.data


def test_info_nav_active_class(client):
    resp = client.get("/info")
    assert b'href="/info" class="active"' in resp.data


def test_index_nav_active_class(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/")
    assert b'class="active">Inspections' in resp.data
```

- [ ] **Step 2: Run to confirm failures**

```bash
cd src/web && python3 -m pytest tests/test_routes.py -q 2>&1 | tail -10
```

Expected: 7 failures on the new tests, all existing tests still pass.

---

### Task 2: Promote nav data to `inject_globals`

**Files:**
- Modify: `src/web/app.py`

- [ ] **Step 1: Replace `inject_globals` and trim `index()`**

In `src/web/app.py`, replace the `inject_globals` function (lines 127–133) with:

```python
@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    year, q = parse_year_quarter(request.args)
    years = get_valid_years()
    return {
        "current_year": date.today().year,
        "version": get_version(),
        "year_quarters": [
            (y, get_valid_quarters(y))
            for y in sorted(years, reverse=True)
        ],
        "selected_year": year,
        "selected_q": q,
    }
```

In the `index()` route (lines 239–248), replace the `render_template` call with:

```python
    return render_template(
        "index.html",
        days=build_days(rows, start, end),
    )
```

(Remove the `selected_year=year`, `selected_q=q`, and `year_quarters=[...]` keyword arguments — they are now provided by `inject_globals`.)

- [ ] **Step 2: Run existing tests to verify nothing broke**

```bash
cd src/web && python3 -m pytest tests/ -q 2>&1 | tail -5
```

Expected: 37 passed (same as baseline). The 7 new tests still fail — `inject_globals` now supplies the data but the templates haven't been updated yet.

---

### Task 3: Rewrite `base.html`

**Files:**
- Modify: `src/web/templates/base.html`

- [ ] **Step 1: Replace `base.html` entirely**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}DineSafeViz{% endblock %}</title>
    <link rel="icon" href="{{ url_for('static', filename='favicon/favicon.svg') }}" type="image/svg+xml">
    <link rel="icon" href="{{ url_for('static', filename='favicon/favicon.ico') }}" sizes="any">
    <link rel="icon" href="{{ url_for('static', filename='favicon/favicon-32x32.png') }}" type="image/png" sizes="32x32">
    <link rel="icon" href="{{ url_for('static', filename='favicon/favicon-16x16.png') }}" type="image/png" sizes="16x16">
    <link rel="apple-touch-icon" href="{{ url_for('static', filename='favicon/favicon-180x180.png') }}" sizes="180x180">
    <link rel="manifest" href="{{ url_for('static', filename='favicon/site.webmanifest') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    {% block head %}{% endblock %}
</head>
<body>
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
            <a href="https://www.linkedin.com/in/kenneth-yyz" target="_blank" rel="noopener">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
                LinkedIn
            </a>
            <a href="https://github.com/im-kenough/DineSafeViz" target="_blank" rel="noopener">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
                GitHub
            </a>
        </div>
    </nav>
    {% block content %}{% endblock %}
    <footer>
        &copy; {{ current_year }} Kenneth Ho<br>
        DineSafeViz v{{ version }}
    </footer>
</body>
</html>
```

- [ ] **Step 2: Run tests**

```bash
cd src/web && python3 -m pytest tests/ -q 2>&1 | tail -10
```

Expected: still failures on the 7 new tests (child templates still use `{% block body %}` which no longer exists in base — they will render empty). Existing tests may also fail at this point. That is expected — push through to Task 4.

---

### Task 4: Update `index.html`

**Files:**
- Modify: `src/web/templates/index.html`

- [ ] **Step 1: Replace `index.html` entirely**

```html
{% extends "base.html" %}
{% block title %}DineSafeViz{% endblock %}
{% block heading %}DineSafe Inspections{% endblock %}
{% block content %}
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
{% endblock %}
```

---

### Task 5: Update `dashboard.html`

**Files:**
- Modify: `src/web/templates/dashboard.html`

- [ ] **Step 1: Replace `dashboard.html` entirely**

```html
{% extends "base.html" %}
{% block title %}DineSafeViz - Dashboard{% endblock %}
{% block heading %}DineSafe Dashboard{% endblock %}
{% block head %}
    <style>
        .dashboard-frame {
            width: 100%;
            height: calc(100vh - 120px);
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--surface);
        }
    </style>
{% endblock %}
{% block content %}
    <iframe class="dashboard-frame"
            src="/grafana/d/dinesafe/dinesafe-inspections?kiosk"
            frameborder="0"></iframe>
{% endblock %}
```

---

### Task 6: Update `info.html`

**Files:**
- Modify: `src/web/templates/info.html`

- [ ] **Step 1: Replace `info.html` entirely**

```html
{% extends "base.html" %}
{% block title %}DineSafeViz - Info{% endblock %}
{% block heading %}DineSafe Information{% endblock %}
{% block head %}
    <style>
        .info-content {
            max-width: 900px;
            line-height: 1.6;
        }
        .info-content h2 {
            margin-top: 2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }
        .info-content ul {
            padding-left: 1.5rem;
        }
        .info-content .meta {
            color: var(--text-muted);
            font-style: italic;
            margin-bottom: 1.5rem;
        }
        .info-content .section-title {
            font-weight: bold;
            margin-top: 1rem;
            color: var(--accent);
        }
        .data-dictionary table {
            margin-top: 1rem;
        }
    </style>
{% endblock %}
{% block content %}
    <div class="info-content">
        <p>
            DineSafe is Toronto Public Health's food safety program that inspects all establishments serving and
            preparing food. Each inspection results in a pass, a conditional pass or a closed notice.
        </p>

        <p class="meta">
            The Inspection List on this site contains 4+ years of data. The dashboard contains data from 2015-01-01 to present.
        </p>

        <h2>Types of Notices</h2>
        <p>
            <a href="https://www.toronto.ca/community-people/health-wellness-care/health-programs-advice/food-safety/dinesafe/about-dinesafe/" target="_blank">About DineSafe Notices</a>
        </p>

        <h3>Pass</h3>
        <p>A Pass notice will be issued when only minor or no infractions are observed during an inspection.</p>
        <p>If minor infractions are repeated at the next inspection, the Public Health Inspector may issue a ticket to obtain compliance. Fines range from $55 to $465 depending on the severity of the infraction.</p>
        <div class="section-title">Minor infraction type:</div>
        <ul>
            <li>Infractions that present a minimal health risk</li>
            <li>These items must be corrected by the next inspection</li>
        </ul>
        <div class="section-title">Examples:</div>
        <ul>
            <li>Walls, floors or other non-food contact surfaces or equipment need cleaning or repair (e.g., cracked or missing floor tiles, cracked or peeling paint not directly over food preparation area)</li>
            <li>Inadequate ventilation and lighting systems</li>
            <li>Hair constraints not worn</li>
        </ul>

        <h3>Conditional Pass</h3>
        <p>A conditional pass notice will be issued when one or more significant infractions are observed during an inspection.</p>
        <p>When issued, a Public Health Inspector will re-inspect an establishment within 24-48 hours of the initial inspection. If the infractions are corrected and no other infractions or only Minor Infractions are found, a Pass Notice will be issued.</p>
        <div class="section-title">Significant infraction types:</div>
        <ul>
            <li>Infractions that present a potential health hazard</li>
            <li>These items must be corrected within 24-48 hours or legal action may be taken</li>
            <li>These items indirectly involve food, through handling, preparation, storage and/or service</li>
        </ul>
        <div class="section-title">Examples:</div>
        <ul>
            <li>Food contact surfaces or equipment require cleaning or repair</li>
            <li>Repair of refrigeration and mechanical dish washing equipment require</li>
            <li>Accurate indicating thermometers not provided</li>
            <li>Lack of hand wash basin with the necessary supplies</li>
            <li>Garbage not stored in a sanitary manner</li>
            <li>Improper cleaning and sanitizing of equipment and utensils</li>
            <li>Washroom cleanliness not maintained, supplies not provided</li>
        </ul>

        <h3>Closed</h3>
        <p>A closed notice will be issued when one or more crucial infractions observed during an inspection are not corrected immediately. A food establishment can only be closed when a health hazard is present.</p>
        <p>An Order to Close the establishment and/or remove the health hazard will be issued. When all of the infractions listed in the Order and all other significant or crucial infractions are corrected, the establishment will receive a Pass Notice and may be re-opened.</p>
        <div class="section-title">Crucial infraction type:</div>
        <ul>
            <li>Infractions that present an immediate health hazard</li>
            <li>These items directly involve food, such as contamination, time-temperature abuse or lack of safe (potable) water or any other condition that is a health hazard</li>
            <li>These items must be corrected immediately or an Order to Close the premises can be issued and/or immediate action must be taken to remove or eliminate the health hazard</li>
            <li>Enforcement action will be taken</li>
        </ul>
        <div class="section-title">Examples:</div>
        <ul>
            <li>No hot and cold running water under pressure in food preparation area or where utensils are washed</li>
            <li>Rodent or insect infestation without effective method of pest control</li>
            <li>Inadequate refrigeration</li>
            <li>Sewage back-up</li>
            <li>Lack of safe potable water</li>
            <li>Food contaminated or adulterated</li>
        </ul>

        <h2>Types of Infractions</h2>
        <p>
            <a href="https://www.toronto.ca/community-people/health-wellness-care/health-programs-advice/food-safety/dinesafe/dinesafe-infractions/" target="_blank">DineSafe Infractions</a>
        </p>

        <h3>Crucial Infractions - Immediate Health Hazard</h3>
        <p>These infractions must be corrected immediately. An order to close the premises may be issued and/or immediate action must be taken to remove or eliminate the health hazard. A Closed Notice will be issued and must be posted, and other enforcement action will be taken.</p>

        <h3>Significant Infractions - Potential Health Hazard</h3>
        <p>These infractions must be corrected immediately and a re-inspection to check for compliance will be conducted within 24 to 48 hours. Legal action may be taken should these infractions remain outstanding.</p>

        <h3>Minor Infractions - Minimal Health Hazard</h3>
        <p>These infractions must be corrected immediately. A follow-up compliance check will be conducted at the next scheduled inspection.</p>

        <h2>Data Dictionary</h2>
        <p>Column definitions for the DineSafe dataset</p>
        <div class="data-dictionary">
            <table>
                <thead>
                    <tr>
                        <th>Column</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>_id</td><td>Unique row identifier for Open Data database</td></tr>
                    <tr><td>Establishment ID</td><td>Unique identifier for an establishment</td></tr>
                    <tr><td>Inspection ID</td><td>Unique ID for an inspection</td></tr>
                    <tr><td>Establishment Name</td><td>Business name of the establishment</td></tr>
                    <tr><td>Establishment Type</td><td>Establishment type i.e. restaurant, mobile cart</td></tr>
                    <tr><td>Establishment Address</td><td>Municipal address of the establishment</td></tr>
                    <tr><td>Infraction Details</td><td>Description of the Infraction</td></tr>
                    <tr><td>Inspection Observation</td><td>Details observed associated with the Infraction</td></tr>
                    <tr><td>Inspection Date</td><td>Calendar date the inspection was conducted</td></tr>
                    <tr><td>Severity</td><td>Level of the infraction, i.e. S - Significant, M - Minor, C - Crucial</td></tr>
                    <tr><td>Action</td><td>Enforcement activity based on the infractions noted during a food safety inspection</td></tr>
                    <tr><td>Outcome</td><td>The registered court decision resulting from the issuance of a ticket or summons for outstanding infractions to the Health Protection and Promotion Act</td></tr>
                    <tr><td>Outcome Date</td><td>The date of the court outcome</td></tr>
                    <tr><td>Amount Fined</td><td>Fine determined in the court outcome</td></tr>
                    <tr><td>Latitude</td><td>Latitude of establishment</td></tr>
                    <tr><td>Longitude</td><td>Longitude of establishment</td></tr>
                    <tr><td>unique_id</td><td>Unique composite key</td></tr>
                </tbody>
            </table>
        </div>
    </div>
{% endblock %}
```

---

### Task 7: Run all tests and commit

- [ ] **Step 1: Run full test suite**

```bash
cd src/web && python3 -m pytest tests/ -v 2>&1 | tail -20
```

Expected: all 44 tests pass (37 original + 7 new).

- [ ] **Step 2: Commit**

```bash
git add src/web/app.py \
        src/web/templates/base.html \
        src/web/templates/index.html \
        src/web/templates/dashboard.html \
        src/web/templates/info.html \
        src/web/tests/test_routes.py \
        docs/superpowers/specs/2026-04-28-nav-consolidation-design.md \
        docs/superpowers/plans/2026-04-28-nav-consolidation.md
git commit -m "ui: consolidate header/nav/footer into base.html (#task-header)"
```
