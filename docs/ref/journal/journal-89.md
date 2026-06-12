# Journal 89

## 2026-06-11 00:00 — Task 4: Add OpenTelemetry SDK with console exporter

### Context
Implementing Task 4 of the observability plan: add OTel SDK (API + SDK + Flask + psycopg2 instrumentors) with a console span exporter as Part 1 (OTLP deferred to Part 2).

### Step 1: Check available OTel version

Attempted install of `opentelemetry-distro==0.51b0` — not available on PyPI. Installed latest:

```
/home/sam/SCM/github/DineSafeViz/src/dsv-app/.venv/bin/pip install opentelemetry-distro opentelemetry-instrumentation-flask opentelemetry-instrumentation-psycopg2
```

Installed versions:
- opentelemetry-api 1.42.1
- opentelemetry-sdk 1.42.1 (pulled in by opentelemetry-distro)
- opentelemetry-distro 0.63b1
- opentelemetry-instrumentation 0.63b1
- opentelemetry-instrumentation-flask 0.63b1
- opentelemetry-instrumentation-psycopg2 0.63b1
- opentelemetry-instrumentation-wsgi 0.63b1
- opentelemetry-instrumentation-dbapi 0.63b1
- opentelemetry-semantic-conventions 0.63b1
- opentelemetry-util-http 0.63b1

Decision: pin `0.63b1` in requirements.txt (matches the plan's intent of pinning the exact installed version when 0.51b0 is unavailable).

### Step 2: Edit requirements.txt

Added three OTel packages at `0.63b1`.

### Step 3: Edit app.py

Added OTel imports after existing import block. Added OTel setup block after `_inspection_rows_returned = Histogram(...)` and before `DATA_START = date(...)`. This satisfies the ordering constraint: FlaskInstrumentor wraps after PrometheusMetrics is already attached.

### Step 4: Run tests

```
1 failed, 58 passed, 1 warning in 0.23s
```

The 1 failure is the pre-existing `test_footer_content` failure (unrelated to OTel). 58 tests pass. OTel span JSON output appeared on stdout during the run — expected from ConsoleSpanExporter.

### Step 5: Commit

```
[poc/v0.4.0 21df283] feat: add OpenTelemetry SDK with console exporter (Part 2 will wire OTLP)
 2 files changed, 14 insertions(+)
```
