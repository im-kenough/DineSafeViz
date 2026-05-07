# Reorder Inspection Table Columns — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorder the inspections table columns, merge establishment name + address into a single column, and expose the previously-hidden `establishment_type` field.

**Architecture:** Two-file change — `app.py` adds `establishment_type` to the SQL SELECT and row dict; `index.html` reorders `<th>`/`<td>` columns and renders the combined Establishment cell with `<br>`. Existing integration tests mock the DB with positional tuples and must be updated to match the new column order.

**Tech Stack:** Flask, Jinja2, psycopg2, pytest

---

## File Map

| File | Change |
|------|--------|
| `src/web/app.py` | Add `establishment_type` to SELECT and row dict in `index()` |
| `src/web/templates/index.html` | Reorder `<th>` / `<td>`, combine establishment cell |
| `src/web/tests/test_routes.py` | Update mock rows (new field at position 6); add 3 new assertions |

---

## Task 1: Update existing mock rows and add new failing tests

The mock DB in these tests returns positional tuples. After adding `establishment_type` at position 6 in the SELECT, any tuple that doesn't include it will cause `r[6]` through `r[9]` to map to the wrong fields.

**Files:**
- Modify: `src/web/tests/test_routes.py`

- [ ] **Step 1: Update `test_route_shows_inspection_data` mock row**

In `test_routes.py`, the mock row for `test_route_shows_inspection_data` currently has 9 fields. Add `"Fast Food"` at position 6 (after `"1 Main St"`):

```python
def test_route_shows_inspection_data(client):
    rows = [(
        date(2024, 2, 14),   # inspection_date
        "C - Crucial",       # severity
        "Court Order",       # action
        "Rats observed",     # infraction_details
        "Risky Bistro",      # establishment_name
        "1 Main St",         # establishment_address
        "Fast Food",         # establishment_type   ← NEW
        "Pass",              # outcome
        "2024-02-20",        # outcome_date
        "500.00",            # amount_fined
    )]
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/inspections?year=2024&q=1")
    assert b"Risky Bistro" in resp.data
    assert b"C - Crucial" in resp.data
    assert b"Rats observed" in resp.data
```

- [ ] **Step 2: Update `test_severity_class_on_row` mock row**

Same addition — insert `"Fast Food"` at position 6:

```python
def test_severity_class_on_row(client):
    rows = [(
        date(2024, 2, 14),   # inspection_date
        "C - Crucial",       # severity
        "Court Order",       # action
        "Rats observed",     # infraction_details
        "Risky Bistro",      # establishment_name
        "1 Main St",         # establishment_address
        "Fast Food",         # establishment_type   ← NEW
        "Pass",              # outcome
        "2024-02-20",        # outcome_date
        "500.00",            # amount_fined
    )]
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/inspections?year=2024&q=1")
    assert b'class="sev-crucial"' in resp.data
```

- [ ] **Step 3: Add new tests for the new column layout**

Append these three tests to `test_routes.py`:

```python
def test_column_headers_in_order(client):
    with patch("app.psycopg2.connect", return_value=_mock_db([])):
        resp = client.get("/inspections")
    html = resp.data.decode()
    severity_pos = html.index("Severity")
    infraction_pos = html.index("Infraction Details")
    establishment_pos = html.index(">Establishment<")
    est_type_pos = html.index("Establishment Type")
    action_pos = html.index(">Action<")
    assert severity_pos < infraction_pos < establishment_pos < est_type_pos < action_pos


def test_establishment_type_rendered(client):
    rows = [(
        date(2024, 2, 14),
        "M - Minor",
        "Notice to Comply",
        "Improper storage",
        "Pasta Palace",
        "99 King St W",
        "Restaurant",         # establishment_type
        "Pass",
        "2024-02-20",
        "0.00",
    )]
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/inspections?year=2024&q=1")
    assert b"Restaurant" in resp.data


def test_establishment_cell_contains_name_and_address(client):
    rows = [(
        date(2024, 2, 14),
        "M - Minor",
        "Notice to Comply",
        "Improper storage",
        "Pasta Palace",
        "99 King St W",
        "Restaurant",
        "Pass",
        "2024-02-20",
        "0.00",
    )]
    with patch("app.psycopg2.connect", return_value=_mock_db(rows)):
        resp = client.get("/inspections?year=2024&q=1")
    assert b"Pasta Palace" in resp.data
    assert b"99 King St W" in resp.data
```

- [ ] **Step 4: Run tests — expect failures**

```bash
python3 -m pytest src/web/tests/test_routes.py -v 2>&1 | tail -20
```

Expected: `test_column_headers_in_order`, `test_establishment_type_rendered`, and `test_establishment_cell_contains_name_and_address` fail. The two updated mock-row tests may still pass (the old assertions don't catch the field-shift bug — that's fine, they'll be structurally correct once `app.py` is updated).

---

## Task 2: Update `app.py` — add `establishment_type` to query and row dict

**Files:**
- Modify: `src/web/app.py:261-282`

- [ ] **Step 1: Update the SQL SELECT**

In the `index()` function, change:

```python
    cur.execute(
        "SELECT inspection_date, severity, action, infraction_details,"
        "       establishment_name, establishment_address, outcome,"
        "       outcome_date, amount_fined"
        " FROM inspections"
        " WHERE inspection_date BETWEEN %s AND %s",
        (start, end),
    )
```

to:

```python
    cur.execute(
        "SELECT inspection_date, severity, action, infraction_details,"
        "       establishment_name, establishment_address, establishment_type,"
        "       outcome, outcome_date, amount_fined"
        " FROM inspections"
        " WHERE inspection_date BETWEEN %s AND %s",
        (start, end),
    )
```

- [ ] **Step 2: Update the row dict**

Change:

```python
    rows = [
        {
            "inspection_date": r[0],
            "severity": r[1],
            "action": r[2],
            "infraction_details": r[3],
            "establishment_name": r[4],
            "establishment_address": r[5],
            "outcome": r[6],
            "outcome_date": r[7],
            "amount_fined": r[8],
        }
        for r in cur.fetchall()
    ]
```

to:

```python
    rows = [
        {
            "inspection_date": r[0],
            "severity": r[1],
            "action": r[2],
            "infraction_details": r[3],
            "establishment_name": r[4],
            "establishment_address": r[5],
            "establishment_type": r[6],
            "outcome": r[7],
            "outcome_date": r[8],
            "amount_fined": r[9],
        }
        for r in cur.fetchall()
    ]
```

- [ ] **Step 3: Run tests — partial progress check**

```bash
python3 -m pytest src/web/tests/test_routes.py -v 2>&1 | tail -20
```

Expected: `test_establishment_type_rendered` and `test_establishment_cell_contains_name_and_address` still fail (template not updated yet). `test_column_headers_in_order` still fails.

---

## Task 3: Update `index.html` — reorder columns and combine establishment cell

**Files:**
- Modify: `src/web/templates/index.html`

- [ ] **Step 1: Replace the `<thead>` row**

Change:

```html
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
```

to:

```html
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Infraction Details</th>
                    <th>Establishment</th>
                    <th>Establishment Type</th>
                    <th>Action</th>
                    <th>Outcome</th>
                    <th>Outcome Date</th>
                    <th>Amount Fined</th>
                </tr>
            </thead>
```

- [ ] **Step 2: Replace the `<tbody>` row**

Change:

```html
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
```

to:

```html
                <tr class="{{ sev_class.get(row.severity, '') }}">
                    <td>{{ row.severity or '—' }}</td>
                    <td>{{ row.infraction_details or '—' }}</td>
                    <td>{{ row.establishment_name or '—' }}<br>{{ row.establishment_address or '—' }}</td>
                    <td>{{ row.establishment_type or '—' }}</td>
                    <td>{{ row.action or '—' }}</td>
                    <td>{{ row.outcome or '—' }}</td>
                    <td>{{ row.outcome_date or '—' }}</td>
                    <td>{{ row.amount_fined or '—' }}</td>
                </tr>
```

- [ ] **Step 3: Run all tests — expect full pass**

```bash
python3 -m pytest src/web/tests/ -v 2>&1 | tail -10
```

Expected: all 54 tests pass (51 original + 3 new).

- [ ] **Step 4: Commit**

```bash
git add src/web/app.py src/web/templates/index.html src/web/tests/test_routes.py
git commit -m "feat(ui): reorder inspection columns and add establishment type (#73)"
```
