# Journal 39: Fix test_column_headers_in_order

## 2026-05-07 18:00

### Summary
Fixed the `test_column_headers_in_order` test by providing mock rows so the table renders properly. This resolves the issue where the test was checking for headers that couldn't possibly exist due to empty rows.

### Problem
The original test passed `_mock_db([])` (empty rows) to the endpoint. The template in `index.html` only renders the `<table>` (and therefore `<th>` headers) inside `{% if rows %}`. With no rows, no table rendered, no `<th>` elements appeared, and the regex returned `[]`. The test would never pass regardless of implementation changes.

### Solution
Replaced the test to provide a properly formatted mock row (10 fields matching the database schema):

**File changed:** `/home/sam/SCM/github/DineSafeViz/src/dsv-app/tests/test_routes.py` (lines 185-213)

**Change made:** Replace empty `_mock_db([])` call with actual row data:
```python
rows = [(
    date(2024, 2, 14),       # inspection_date
    "M - Minor",             # severity
    "Notice to Comply",      # action
    "Improper storage",      # infraction_details
    "Test Place",            # establishment_name
    "1 Main St",             # establishment_address
    "Restaurant",            # establishment_type
    "Pass",                  # outcome
    "2024-02-20",            # outcome_date
    "0.00",                  # amount_fined
)]
```

### Test Results

**Step 3: Run specific test**
```
python3 -m pytest src/dsv-app/tests/test_routes.py::test_column_headers_in_order -v
```

Result: FAILED (as expected)
```
AssertionError: assert 'Establishment Type' in ['Severity', 'Action', 'Infraction Details', 'Establishment Name', 'Address', 'Outcome', ...]
```

The table now renders (we see headers), but "Establishment Type" is not yet in the headers. This is the expected failure for Task 1 completion.

**Step 4: Run full test suite**
```
python3 -m pytest src/dsv-app/tests/test_routes.py -v 2>&1 | tail -10
```

Results: **24 passed, 1 failed** ✓
- Confirms no regressions
- test_column_headers_in_order is the only failure
- All 24 other tests pass

### Status
Task 1 fix complete. Test is now functional and will pass after Tasks 2 and 3 (SQL query update and template update) are implemented.

## 2026-05-07 18:43 Task 3 Complete: Update index.html - column reordering and establishment cell combo

### Changes Made

**1. File: `/home/sam/SCM/github/DineSafeViz/src/dsv-app/templates/index.html`**

- **Lines 19-29** (`<thead>`): Replaced header row
  - Old order: Severity, Action, Infraction Details, Establishment Name, Address, Outcome, Outcome Date, Amount Fined
  - New order: Severity, Infraction Details, Establishment, Establishment Type, Action, Outcome, Outcome Date, Amount Fined

- **Lines 33-42** (`<tbody>`): Replaced data row
  - Combined establishment_name and establishment_address into single cell with `<br>` separator
  - Added row.establishment_type column at position 4 (after Establishment, before Action)
  - Reordered all other fields to match new header order

### Test Results

**Command:** `python3 -m pytest src/dsv-app/tests/ -v`
**Result:** ✓ **54 PASSED** (51 original + 3 new task tests)
- `test_column_headers_in_order` ✓ PASSED
- `test_establishment_type_rendered` ✓ PASSED
- `test_establishment_cell_contains_name_and_address` ✓ PASSED
- All 51 other pre-existing tests ✓ PASSED

### Commit

**Commit SHA:** 2ddf7796eaa305359c4f0f2a025c61879eda0793

**Files committed:**
- src/dsv-app/app.py (pre-existing changes from Task 2)
- src/dsv-app/templates/index.html (this task)
- src/dsv-app/tests/test_routes.py (pre-existing changes from Task 1)

**Commit message:** `feat(ui): reorder inspection columns and add establishment type (#73)`

### Self-Review

✓ Column order in headers matches task spec exactly
✓ Data row fields reordered to match headers
✓ Establishment cell displays name + address with `<br>` line break
✓ establishment_type column properly displays from row.establishment_type
✓ All 54 tests pass, no regressions
✓ No unrelated code changes
✓ Commit message follows project convention

**Status:** Task 3 COMPLETE
