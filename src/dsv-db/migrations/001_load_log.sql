-- 001: the load_log table, and narrow dinesafe_migrator to what the data
-- pipeline needs. Idempotent: the Postgres image runs it once on a new
-- volume (mounted after init.sql), and scripts/deploy.sh runs it on every
-- deploy, so existing databases pick it up too.

CREATE TABLE IF NOT EXISTS load_log (
    id               SERIAL PRIMARY KEY,
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind             TEXT NOT NULL CHECK (kind IN ('seed', 'refresh')),
    recent_path      TEXT NOT NULL,   -- recent/20261012T113012Z/Dinesafe.csv
    historical_path  TEXT,            -- historical/20261012T113012Z/ (seed only)
    rows_deleted     INTEGER NOT NULL,
    rows_inserted    INTEGER NOT NULL
);

-- The pipeline loads as dinesafe_migrator: read, insert, and delete rows in
-- its two tables, and nothing else (no CREATE, TRUNCATE, UPDATE, or DROP).
REVOKE ALL ON TABLE inspections, load_log FROM dinesafe_migrator;
REVOKE ALL ON SEQUENCE inspections_id_seq, load_log_id_seq FROM dinesafe_migrator;
REVOKE CREATE ON SCHEMA public FROM dinesafe_migrator;
GRANT SELECT, INSERT, DELETE ON TABLE inspections, load_log TO dinesafe_migrator;
GRANT USAGE ON SEQUENCE inspections_id_seq, load_log_id_seq TO dinesafe_migrator;

-- Read-only, like inspections, so the app and Grafana can show data freshness.
GRANT SELECT ON TABLE load_log TO dinesafe_app;
