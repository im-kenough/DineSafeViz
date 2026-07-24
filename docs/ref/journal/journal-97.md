# Journal 97

## 2026-07-24 — Webapp shows data only up to June 10 despite CSV having data to July 22

**Task:** User reports `Dinesafe.csv` contains data up to 2026-07-22, but the
webapp only displays data up to 2026-06-10. Investigate root cause (systematic
debugging — no fixes until root cause confirmed).

### Context carried over from journal-96

Prior session today did local Docker testing (isolated project `dsv-localtest`)
using `docs/ref/local-data/Dinesafe.csv` + historical files, wired via new
`DSV_LOCAL_DATA_DIR` env toggle in `refresh.py`. That test seeded 502,795 rows
spanning 2001-01-03 → 2026-07-22 and the webapp query `/inspections?year=2026&q=3`
showed rows correctly. That was a throwaway isolated stack, torn down with
`down -v` afterward — user's real `.env`/volumes untouched.

Current uncommitted changes (`git status`): `.env.example`, `docker-compose.yml`,
`src/dsv-app/Dockerfile`, `src/dsv-app/requirements.txt`, `src/dsv-db/refresh.py`,
`src/dsv-db/tests/test_refresh.py` — these are the journal-96 changes, not yet
committed.

### Phase 1: Root cause investigation

`docker ps -a`: real stack (compose project `dsv`, not the throwaway
`dsv-localtest`) is up. `dsv-dsv-init-db-1` **exited(1)** ~8 min ago (silent
failure — `docker compose up` doesn't surface a non-blocking job's exit code
to the user).

`docker logs dsv-dsv-init-db-1`:
```
psycopg2.OperationalError: connection to server at "dsv-db" (172.18.0.2), port 5432 failed: FATAL:  password authentication failed for user "dsv-db-user"
```

`docker logs dsv-dsv-db-1` (postgres): actually `FATAL: role "dsv-db-user" does not exist` (repeating every ~5s — pg_isready healthcheck retries, container reports "healthy" regardless since pg_isready only checks the server accepts connections, not that a specific role can auth).

`docker exec dsv-dsv-db-1 psql -U postgres -c "\du"`: roles are `postgres`
(superuser), `dinesafe_app`, `dinesafe_migrator`. **No role `dsv-db-user`
exists in this volume.**

`docker inspect dsv-dsv-db-1`: container's actual env is
`POSTGRES_USER=dsv-db-user`, `POSTGRES_DB=dinesafe`,
`POSTGRES_PASSWORD=changeme` (still the `.env.example` placeholder — flagged
separately, not this bug).

**Key fact:** Postgres's official image only runs `POSTGRES_USER` /
`POSTGRES_PASSWORD` / `POSTGRES_DB` bootstrap (and anything in
`docker-entrypoint-initdb.d/`, i.e. `init.sql`) on first init of an **empty**
data directory. The named volume `dsv_dsv-db-data` already contained a
database from a prior run — so today's `.env` value `DSV_DB_USER=dsv-db-user`
was never applied to it. That volume's actual bootstrap superuser is
`postgres` (or whatever it was when the volume was first created), and
`dsv-db-user` has never existed inside it.

Confirmed `init.sql` (unchanged since #158, not touched by today's schema-fix
commit `57b133c`) hardcodes roles `dinesafe_app` / `dinesafe_migrator` and
`GRANT ... ON DATABASE dinesafe` — matches what's actually in the volume, so
the DB name/roles line up fine. Only the **bootstrap superuser identity**
(`DSV_DB_USER`) is out of sync between `.env` and the persisted volume.

`dsv-init-db` (the `refresh.py` reseed job, per `init.sql` comment: "refresh.py
currently still connects as the bootstrap superuser") authenticates as
`DSV_DB_USER`/`DSV_DB_PASSWORD` — so it has been failing this way on every
`docker compose up` since whenever `.env`'s `DSV_DB_USER` diverged from the
volume's real superuser. The app (`dsv-app`) connects as `dinesafe_app`
instead (a role that *does* exist), so it keeps serving whatever was already
in the table — silently masking the reseed failures.

**Confirmed via query:**
```
docker exec dsv-dsv-db-1 psql -U postgres -d dinesafe -c \
  "SELECT MIN(inspection_date), MAX(inspection_date), COUNT(*) FROM inspections;"
   min     |    max     | count
2001-01-03 | 2026-06-10 | 465985
```
Max date **2026-06-10** exactly matches the user's report. Root cause confirmed:
this is the last date for which `dsv-init-db` successfully authenticated and
reseeded, before `.env`'s `DSV_DB_USER` and the persisted volume's actual
superuser drifted apart. Every run since then has silently no-opped.

**Root cause:** Postgres-volume/`.env` credential drift — `DSV_DB_USER` in the
live `.env` does not match the bootstrap superuser baked into the existing
`dsv_dsv-db-data` volume at first-init time, so `dsv-init-db` (refresh.py) has
been failing auth and exiting non-zero on every `docker compose up`, never
reaching the reseed logic. Not caused by today's schema-fix commit (`init.sql`
and `DSV_DB_USER` untouched by it) — this is separate, longer-standing drift,
just newly *noticed* because the user downloaded a fresh CSV today and compared
dates.

Reported findings to user; awaiting decision on remediation path (recreate
volume vs. reconcile credentials in place) before taking any action, since
both touch the user's real running stack.

### Decision + remediation

User chose: recreate the `dsv_dsv-db-data` volume (not the reconcile-in-place
option) — full reseed is reproducible from CSVs, so no real data loss; the
separate `dsv-analytics-data` (Grafana) volume was left untouched.

`docker compose down` (no `-v`) → `docker volume rm dsv_dsv-db-data` →
`docker compose up -d`.

**Second bug hit on first attempt:** `dsv-db-1` failed to even finish
initializing on the fresh volume:
```
ERROR:  role "dinesafe" does not exist
STATEMENT:  ALTER DEFAULT PRIVILEGES FOR ROLE dinesafe, dinesafe_migrator ...
```
`init.sql` line 38 (added whole in #158, `git log -p --follow` shows no earlier
variant) hardcodes a role `dinesafe` that is never `CREATE ROLE`'d anywhere —
only `dinesafe_app`/`dinesafe_migrator` exist. Comment above it says the intent
was to also cover "the bootstrap superuser" (dynamic, whatever `DSV_DB_USER`
is) — got hardcoded to a literal that was never real. Latent since #158; never
triggered because no volume had been freshly initialized since (every existing
deployment's volume predates this line, so `docker-entrypoint-initdb.d` never
ran it before today).

Fix (user-approved, chose `CURRENT_USER` over hardcoding the literal
`dsv-db-user`): `src/dsv-db/init.sql:38` —
`FOR ROLE dinesafe, dinesafe_migrator` → `FOR ROLE CURRENT_USER, dinesafe_migrator`.
`CURRENT_USER` resolves to whoever `init.sql` is actually running as (the
bootstrap superuser), so this stays correct regardless of what `DSV_DB_USER`
is named per-deployment — same class of drift as the original bug, fixed at
the root instead of hardcoded again.

Removed the half-initialized volume, retried `docker compose up -d`:
`dsv-db-1` healthy, `dsv-init-db-1` **exited(0)** — full seed ran (23
historical files + `Dinesafe.csv` recent = 502,795 rows), `dsv-app-1` healthy.

**Verified:**
```
docker exec dsv-dsv-db-1 psql -U dsv-db-user -d dinesafe -c \
  "SELECT MIN(inspection_date), MAX(inspection_date), COUNT(*) FROM inspections;"
   min     |    max     | count
2001-01-03 | 2026-07-22 | 502795
```
Matches the source CSV exactly. Root cause resolved.

**Noted, not chased (out of scope):** `dsv-init-analytics-1` exits(22) with no
log output, both before and after this fix — pre-existing, unrelated to
today's issue (Grafana dashboard-permissions grant job). Left as-is per
surgical-changes rule; flagging here for future reference.

**Not yet done:** neither fix is committed. `init.sql`'s `CURRENT_USER` change
and this journal entry are the only uncommitted changes right now.

## `dsv-init-analytics` exit(22) — investigated per user request

### Reproduction

Stack had been `docker compose down`'d (by user or externally) between the
prior task and this one — no containers running, volumes intact. Brought it
back up (`docker compose up -d`) to reproduce: `dsv-init-analytics-1`
exited(22) again, no log output, same as originally observed.

### First hypothesis (WRONG — corrected after further verification)

Manually replicated the job's curl calls one at a time against the live
`dsv-analytics` service on the `dsv_default` network (`docker run --rm
--network dsv_default curlimages/curl:latest ...`):
- Health check: OK.
- Dashboard lookup (`GET .../dashboards/uid/dinesafe` with `admin:changeme`
  basic auth): **200**, found dashboard id `1`.
- Permissions grant (`POST .../dashboards/id/1/permissions`): **403**
  `"Permissions needed: dashboards.permissions:write"`. `curl -sf` turns any
  4xx into exit 22 with the body suppressed — matches the silent exit(22).

Initial (incorrect) read: assumed Grafana 11.2's default RBAC deprecates the
legacy id-based permissions endpoint for classic admin auth. Tried the
RBAC-era Resource Permissions API (`/api/access-control/dashboards/uid/...`)
as a replacement — got **404**, that surface isn't exposed the way I expected
either.

**Caught the error before committing to it:** checked `/api/access-control/user/permissions`
for the `admin` user directly — it came back with only `dashboards:read`
scoped to the `dinesafe` dashboard, i.e. **Viewer-level permissions**, not an
authenticated Admin's. And `/api/user` (which has no anonymous fallback)
returned a flat `401 Unauthorized`. That contradicted the RBAC theory —
if `admin:changeme` were truly authenticating, `/api/user` should have
succeeded.

### Actual root cause (verified via Grafana's own auth log)

`docker logs dsv-dsv-analytics-1 | grep -i auth`:
```
logger=authn.service msg="Failed to authenticate request" client=auth.client.basic error="[password-auth.failed] invalid password"
```
**Same bug class as the DB fix earlier this session** — `GF_SECURITY_ADMIN_PASSWORD`
(from `.env`'s `DSV_ANALYTICS_ADMIN_PASSWORD`) is bootstrap-only, applied only
on first init of an empty Grafana volume. `dsv-analytics-data` had never been
recreated (only `dsv-db-data` was, earlier), so its admin password no longer
matched `.env`. Wrong credentials silently fall back to the anonymous-Viewer
identity on read-tolerant endpoints (explaining the misleading 403 on the
permissions POST — a Viewer legitimately lacks `dashboards.permissions:write`),
while `/api/user` correctly hard-401s since it has no anonymous fallback. The
legacy permissions endpoint itself was never actually broken.

**Verification before concluding:** recreated `dsv_dsv-analytics-data`
(`docker compose down` → `docker volume rm dsv_dsv-analytics-data` → `up -d`),
then re-ran the **original, unmodified** `dsv-init-analytics` entrypoint
against the fresh volume — it succeeded (`{"message":"Dashboard permissions
updated"}`, exit 0) with no code changes. Confirms the RBAC/endpoint
rewrite would have been solving a problem that didn't exist; reverted that
plan.

### Aside surfaced during this fix, resolved in the same pass

Recreating `dsv-analytics-data` triggered a second `dsv-init-db` run (table
now non-empty from the earlier reseed → `refresh()` incremental path instead
of `seed()`). It failed at `get_connection()`:
```
FATAL: password authentication failed for user "dsv-db-user"
```
Verified directly (network auth from a throwaway container): the `dsv-db-data`
volume's real password was still `changeme`, while `.env`'s current
`DSV_DB_PASSWORD` was `testing-strong-password1-DSV_DB_PASSWORD` — i.e. `.env`
was edited (by the user, presumably hardening off the placeholder) sometime
between the earlier clean reseed and now, after the volume had already
bootstrapped with the old value. User confirmed the change was intentional
and chose to recreate `dsv-db-data` again.

This also explained a transient row-count drop I'd noticed (502,795 → 498,004)
across the two down/up cycles used to reproduce the analytics bug — each
re-triggers `refresh()`'s delete+reinsert of the recent-date window; one of
those runs likely raced the credential drift. Not a bug in `refresh()` itself:
after the clean re-seed the count returned to exactly **502,795** (matches
the source CSVs bit-for-bit), so this was an artifact of testing, not a real
data-integrity issue.

### Final verified state

`docker compose down` → `docker volume rm dsv_dsv-db-data` → `up -d`:
- `dsv-init-db-1` exited(0): full reseed, `502,795` rows, `2001-01-03` →
  `2026-07-22`.
- `dsv-init-analytics-1` exited(0): `{"message":"Dashboard permissions updated"}`.
- `dsv-db-1`, `dsv-app-1` healthy; `dsv-analytics-1`, `dsv-nginx-1` up.

No code changes needed for the analytics job — it was never actually broken,
just starved of a valid password by the same one-shot-bootstrap-volume
gotcha as the DB. Only remaining uncommitted change is `init.sql`'s
`CURRENT_USER` fix from the earlier task, plus this journal entry.

## Documentation audit: "did you update docs for the dataset changes?"

User asked directly whether documentation was updated to reflect the schema
work from earlier today (journal-96). Answer at the time: no. Audited
`docs/ref/data.md` and `docs/ref/arch/arch-data.md` (the two files
describing the CSV schema / DB schema / data gap) against the actual current
`RECENT_COLUMN_MAP`/`HISTORICAL_COLUMN_MAP` in `refresh.py` and, critically,
against the live DB — both were stale in multiple ways predating today, not
just missing today's changes:

- `establishment_status` documented as "historical only, NULL for current" —
  wrong; `inspectionStatus → establishment_status` has been mapped for
  recent rows all along (predates today). Verified: 107,169/107,169 recent
  rows have it populated.
- Recent CSV documented as 17 columns lacking `oldEstId`/`phone`/`observation`/
  `severity`, still showing `Action` populated for recent rows — reflects
  the pre-journal-96 schema.
- "Data gap: Jan–Nov 2023" documented as an unfixable upstream limitation —
  **no longer true** (see below).

### Bug found during the audit (not just a docs gap): double-counted 2023-11-10 to 2023-12-29

Toronto's historical archive now ships a `dinesafe_hist_2023.csv` (wasn't
present when the gap was originally documented) covering all of 2023. Its
tail (2023-11-10 through 2023-12-29) overlaps the recent CSV's rolling
window (starts 2023-11-10). `refresh.py`'s `seed()` loaded both sources
wholesale with no dedup, so every inspection in that ~7-week window was
inserted twice. Verified by pulling one establishment's rows directly: the
same 14 infractions appeared twice, once from each source, differing only
in `action` (populated historical-side, always NULL recent-side — consistent
per-source behavior, confirming genuine duplication not coincidence). Scale:
4,791 historical + 4,283 recent rows for what should be one ~7-week window —
roughly 1% of the 502,795-row table, concentrated entirely in that span
(would visibly distort the Grafana "Inspections Over Time" trend panel).

User chose: fix the dedup logic first, then write docs against the corrected
dataset (not document a known bug, not skip it).

### Fix attempt #1 — wrong on the first pass, caught before shipping

TDD per project convention. Added `exclude_on_or_after(rows, cutoff)` (pure,
tested) and wired it into `seed()`: fetch recent rows first, derive
`cutoff = min_inspection_date(recent_rows)`, pass it through
`download_and_load_historical` → `_insert_historical_csv` to drop historical
rows on/after cutoff before insert. Unit tests passed (4/4 new + 29 existing).

**Rebuilt the image, re-seeded, and the fix was a no-op** — `dinesafe_hist_2023.csv`
still loaded all 37,836 rows, DB max historical date still 2023-12-29.
Root cause: `dinesafe_hist_2023.csv` uses **`MM/DD/YYYY`** dates
(`01/03/2023`), while every other historical file (2001–2022) and the recent
CSV use ISO `YYYY-MM-DD`. `exclude_on_or_after`'s plain string comparison
made `'01/03/2023' < '2023-11-10'` always `True` (leading `'0'`/`'1'` sorts
before `'2'` lexicographically) regardless of actual date — filtered nothing,
for the one file where it mattered. Confirmed directly:
```python
_read_csv_rows('.../dinesafe_hist_2023.csv', HISTORICAL_COLUMN_MAP)[0]['inspection_date']
# '01/03/2023'
```
My first unit test used ISO strings on both sides of the comparison, so it
didn't catch the format mismatch — passed against a fixture, not against
real data. Caught by re-verifying against the actual CSV files before
declaring done, per verification-before-completion practice.

### Fix attempt #2 — root cause: normalize date format at parse time

Added `normalize_date(value)` (MM/DD/YYYY → ISO, ISO passed through, None
passed through) and wired it into `map_row()` so every row's
`inspection_date` is canonical ISO the moment it's parsed — fixes the
comparison at its source rather than teaching every consumer (the new
filter, `min_inspection_date`, `refresh()`'s cutoff) about multiple formats.
TDD: 4 new tests (`TestNormalizeDate`, `TestMapRowNormalizesDate`), watched
fail (ImportError), implemented, 34/34 pass.

**Verified against real files before rebuilding:**
```
hist 2023 rows before filter: 37836
hist 2023 rows after filter: 33045   # exactly the 4,791-row overlap dropped
max date after filter: 2023-11-09    # one day before recent CSV's cutoff
```
Rebuilt `dsv-init-db`, recreated `dsv-db-data`, re-seeded:
- Historical: `2001-01-03` → `2023-11-09`, 390,835 rows.
- Recent: `2023-11-10` → `2026-07-22`, 107,169 rows.
- No gap, no overlap. Duplicate-check query (same establishment/date/count>20
  in the old overlap window) returns **zero rows**.
- Every 2023 month still has data (2,294–3,829 rows/month) — the "data gap"
  really is closed, just not via double-counting anymore.
- Total: **498,004** rows (down from the double-counted 502,795).

### Bonus: hit the analytics-permissions bug again, for a real reason this time

Recreating `dsv-db-data` re-triggered `dsv-init-analytics`, which exited 22
again. Unlike earlier today, `dsv-analytics-data` hadn't been touched and
credentials checked out fine (`/api/user` 200, genuine admin). Manually
replicated the script's dashboard-lookup step authenticated correctly this
time and found the *first* `"id":` match in the JSON was the dashboard's own
top-level id — now `45379590766592`, not a small sequential integer. This
Grafana instance (feature toggles include `kubernetesPlaylists`,
`kubernetesDashboards`-adjacent toggles per its startup log) appears to
assign dashboards large, unstable numeric ids that change across
restarts/reprovisions, while `uid: "dinesafe"` stays stable. The legacy
`/api/dashboards/id/:id/permissions` endpoint 404s once the id drifts.
Confirmed the fix: `/api/dashboards/uid/dinesafe/permissions` (GET showed the
Viewer permission was already set from an earlier successful run; POST
returned `{"message":"Dashboard permissions updated"}`) works regardless of
the unstable id.

Rewrote `docker-compose.yml`'s `dsv-init-analytics` entrypoint: dropped the
regex-based `DASH_ID` extraction entirely, replaced the id-based existence
check + POST with a direct `HEAD`-style status check + POST against the
uid-based endpoint. Net simplification (one fewer curl call, no JSON
scraping) as well as a fix. Verified stable across two full
`docker compose down` / `up -d` cycles — both `dsv-init-db` and
`dsv-init-analytics` exit 0 each time, data counts unchanged between runs.

### State after this task

`src/dsv-db/init.sql` (`CURRENT_USER` fix) was committed independently by
the user mid-session as `1e0d5eb "fix: db role mismatch"`, along with a
separate `cb1d735 "bump app versions and pin them #175"` commit
(`docker-compose.yml` image pins, new `docs/ref/images.md`,
`src/dsv-app/Dockerfile`) — both outside this conversation. Noted so I
don't describe either as uncommitted. Still uncommitted from this session:
`src/dsv-db/refresh.py` (dedup + date-normalization fix),
`src/dsv-db/tests/test_refresh.py` (+7 tests), `docker-compose.yml`
(analytics-permissions endpoint fix). Full test suite: 34/34 passing.

## Documentation update (completes the original ask)

Rewrote `docs/ref/data.md` and `docs/ref/arch/arch-data.md` against the
verified-correct dataset and current `refresh.py` ground truth (cross-checked
every claim against either the code's column maps or live `COUNT()`/`GROUP BY`
queries against the running DB, not assumption):

- Current-data dictionary/sample rewritten around the real 18-column
  `RECENT_COLUMN_MAP` (raw CSV headers, not the old invented "pretty name"
  labels that had drifted from the actual feed).
- Fixed several *pre-existing* (not just today's) inaccuracies, confirmed
  by direct per-column `COUNT()` against all 498,004 live rows:
  `establishment_status` is populated for **both** eras, not
  historical-only as previously documented; `inspection_id` and
  `establishment_type` are historical-only (**not** "both eras" as
  previously documented) — the current feed has never carried either.
- `action`: was documented as "both eras"; now correctly historical-only
  (the City dropped it from the feed in 2026, per journal-96).
- "Data gap: Jan–Nov 2023" section replaced with "Data gap: none
  currently" — explains the 2023 historical file that closed it, the
  overlap it introduced, and links to this journal for how the resulting
  duplicate-counting bug was found and fixed. Explicitly flagged as
  time-of-writing (2026-07-24), not a permanent guarantee.
- Documented the 2023 historical file's format quirks (`MM/DD/YYYY` dates,
  unquoted) since "no schema drift across historical files" was no longer
  true.
- Fixed stale infra claims found along the way: `postgres:17.9` /
  `grafana 11.6` hardcoded in arch-data.md (actual: pinned in
  `docker-compose.yml`, tracked in the user's new `docs/ref/images.md` —
  pointed there instead of hardcoding a version that will drift again); a
  dead path reference (`src/dsv-db/2023-04-11 - Dinesafe Historical
  data/`, doesn't exist — production downloads live, local testing uses
  `docs/ref/local-data/`).
- Added a note to the Grafana analytics section: the enforcement/
  establishment-type panels only have data through 2023-11-09 and will look
  increasingly sparse as current-era (post-2023-11-10) inspections
  accumulate, since both fields are permanently NULL for that era.

Confirmed `old-ignore/` and `superpowers/specs|plans/` still reference the
old versions/schema — left untouched, those are archived/point-in-time by
design, not living docs.

