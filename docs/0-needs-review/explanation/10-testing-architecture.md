# Testing architecture

This document describes the testing performed in DineSafeViz, grouped by
category. It covers what exists today and identifies gaps to close in future
work.

## Unit tests

Unit tests validate individual functions in isolation, with no I/O or
external dependencies. They run with pytest and use `unittest.mock` where
needed to stub out side effects.

### Web app helpers (`src/dsv-app/tests/test_helpers.py`)

Tests for pure date and data-formatting logic:

- `get_quarter_bounds` — boundary calculations for all four quarters,
  clipping to `DATA_START` and today's date
- `get_valid_years`, `get_valid_quarters` — valid year/quarter range
  generation
- `parse_year_quarter` — parameter validation and fallback behavior for
  invalid or out-of-range inputs
- `sort_rows` — severity sort order (Crucial > Significant > Minor > NA)
- `build_days` — grouping rows by date, newest-first ordering, empty-day
  handling

### Home page stats (`src/dsv-app/tests/test_home.py`)

Tests for the `_get_home_stats` caching layer:

- First-call fetch and cache population (database mocked)
- Cache hit within TTL (no database call)
- Cache refresh after TTL expiry

### ETL data mapping (`src/dsv-db/tests/test_refresh.py`)

Tests for the database refresh script's data transformation logic:

- `normalize` — converts `"None"` and empty strings to Python `None`
- `min_inspection_date` — finds the earliest date, skipping `None` values
- `map_row` — maps both historical and recent CSV column schemas to the
  canonical `INSPECTIONS_COLUMNS` format, verifying that schema-specific
  columns are present and that missing columns default to `None`

## Functional tests (route/view)

These tests exercise Flask routes through the built-in test client. They
mock the database, so they validate request handling, template rendering,
and response content, not database integration.

### Shared fixture (`src/dsv-app/tests/conftest.py`)

A pytest `client` fixture creates a Flask test client with
`TESTING = True`.

### Route responses (`src/dsv-app/tests/test_routes.py`)

- HTTP 200 for the home page, inspections, dashboard, and info routes
- Inspections page renders day boxes, inspection data, severity CSS
  classes, column headers in the correct order, establishment names with
  addresses, and establishment type
- Graceful handling of invalid query parameters (returns 200 with
  defaults)
- "No data" text displayed for empty result sets
- Navigation elements: dropdown menus, year/quarter links, active nav
  classes, archive section, footer content
- Dropdown and nav consistency across all pages (home, dashboard, info)

### Home page rendering (`src/dsv-app/tests/test_home.py`)

- `test_home_route_renders_stats` — verifies the home route renders
  formatted stats and navigation links

### Dashboard rendering (`src/dsv-app/tests/test_dashboard.py`)

- Dashboard returns 200, contains an iframe pointing to the analytics
  embed, and includes home/info navigation links

## Manual smoke tests (post-implementation verification)

Documented in [the PIV runbook](../how-to/3-verify-a-deployment.md), these
are manual curl-based checks run after each deployment:

- Stack startup (`docker compose up --build -d`)
- HTTP 200 from the home page, analytics health endpoint, and all app
  routes (`/inspections`, `/dashboard`, `/info`)
- Home page contains navigation links to `/inspections` and `/dashboard`
- Stack teardown

## Container health checks

Defined in `docker-compose.yml`, these aren't tests in the traditional
sense but provide runtime health verification:

- **PostgreSQL:** `pg_isready` check with 5-second interval and 5 retries.
  Other services use `depends_on: condition: service_healthy` to gate
  startup on a healthy database.
- **Grafana readiness:** The `dsv-init-analytics` and `init-grafana`
  init containers poll the Grafana health API before applying dashboard
  permissions.

## Dependency scanning

Dependabot (`.github/dependabot.yml`) opens weekly PRs for outdated
versions across four ecosystems:

- Python packages (`src/dsv-app`)
- Docker base images (`src/dsv-app`, `src/dsv-db`)
- GitHub Actions versions

## Test runner

All automated tests run via pytest. The only dev dependency is
`pytest==9.0.3` (`src/dsv-app/requirements-dev.txt`). There is no
`pytest.ini`, `pyproject.toml`, or `tox.ini` — pytest uses its default
configuration with standard test discovery.

To run tests locally:

```sh
cd src/dsv-app && python -m pytest tests/
cd src/dsv-db && python -m pytest tests/
```

## Gaps

The following areas have no automated testing today. This list represents
candidates for future work, not immediate action items.

| Gap | Category | Notes |
|-----|----------|-------|
| No CI pipeline | Automation | Tests aren't run on push or PR; passing is not a merge gate |
| No linting or static analysis | Code quality | No flake8, ruff, mypy, or similar tooling configured |
| No integration tests | Integration | All database interactions are mocked; no tests run against a real PostgreSQL instance |
| No container image scanning | Security | No Trivy, Grype, or similar scanner in the build pipeline |
| No infrastructure compliance tests | Infrastructure | No InSpec, Testinfra, or similar tool validating the deployed VM or container configuration |
| No end-to-end browser tests | E2E | No Playwright or Selenium tests exercising the full rendered UI |
| No load or performance tests | Performance | No baseline for response times or concurrency limits |
| No pre-commit hooks | Code quality | No automated checks before commit (linting, formatting, secrets detection) |
| PIV not automated | Automation | Smoke tests in `3-verify-a-deployment.md` are manual curl commands, not a scripted test suite |
