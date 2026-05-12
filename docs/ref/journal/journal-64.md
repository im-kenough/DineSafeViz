# Journal 64

## 2026-05-12 — Document testing architecture

**Goal:** Review the repo and update `docs/ref/arch/arch-testing.md` with an
inventory of existing tests, grouped by type, and identify gaps.

### Research

Surveyed the codebase for all test-related artifacts:

- `src/dsv-app/tests/` — 5 test modules + conftest, all pytest, using Flask
  test client and `unittest.mock`
- `src/dsv-db/tests/` — 1 test module for the data refresh ETL script
- `docs/how-to/2-piv.md` — manual post-implementation verification (curl smoke
  tests)
- `docker-compose.yml` — PostgreSQL healthcheck (`pg_isready`)
- `.github/workflows/` — release-drafter and release publish only; no CI test
  pipeline
- `.github/dependabot.yml` — dependency version scanning
- `infra/Makefile` — IaC orchestration, no test targets
- No linter config, no static analysis, no pre-commit hooks, no integration
  test suite, no infrastructure compliance tests

### Findings

**Existing tests fall into three categories:**
1. Unit tests — pure function logic (helpers, ETL mapping/normalization)
2. Route/view tests — Flask test client exercising HTTP endpoints with mocked DB
3. Manual smoke tests — curl-based PIV checklist

**Gaps identified:**
- No CI pipeline running tests on push/PR
- No linting or static analysis
- No integration tests against a real database
- No container or infrastructure compliance tests
- No security scanning
- No end-to-end browser tests
- No load/performance testing

### Action

Updated `docs/ref/arch/arch-testing.md` with full inventory and gap analysis.
