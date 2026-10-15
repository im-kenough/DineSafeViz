-- Passwords are set by set-passwords.sh, which runs after this file.
CREATE ROLE dinesafe_migrator WITH LOGIN;
CREATE ROLE dinesafe_app      WITH LOGIN;

CREATE TABLE inspections (
    id                          SERIAL PRIMARY KEY,
    establishment_id            TEXT,
    inspection_id               TEXT,
    establishment_name          TEXT,
    establishment_type          TEXT,
    establishment_address       TEXT,
    infraction_details          TEXT,
    infraction_category         TEXT,
    inspection_date             DATE,
    severity                    TEXT,
    action                      TEXT,
    outcome                     TEXT,
    outcome_date                TEXT,
    amount_fined                TEXT,
    latitude                    DOUBLE PRECISION,
    longitude                   DOUBLE PRECISION,
    unique_id                   TEXT,
    establishment_status        TEXT,
    min_inspections_per_year    TEXT,
    -- Split from establishment_address at load by loader.py
    street                      TEXT,
    unit                        TEXT,
    postal_code                 TEXT
);

-- Every app, refresh, and Grafana query filters on inspection_date.
CREATE INDEX inspections_inspection_date_idx ON inspections (inspection_date);

GRANT CONNECT ON DATABASE dinesafe TO dinesafe_app;
GRANT USAGE   ON SCHEMA public       TO dinesafe_app;
GRANT SELECT ON TABLE inspections TO dinesafe_app; -- SELECT only: Flask app is read-only; dsv-pipeline writes as dinesafe_migrator

-- Caps every app and Grafana query, including anonymous Grafana API queries.
ALTER ROLE dinesafe_app SET statement_timeout = '10s';

GRANT CONNECT ON DATABASE dinesafe TO dinesafe_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO dinesafe_migrator;
GRANT ALL PRIVILEGES ON TABLE inspections TO dinesafe_migrator;
GRANT ALL PRIVILEGES ON SEQUENCE inspections_id_seq TO dinesafe_migrator;

-- Default privs must cover every role that actually creates tables: the
-- bootstrap superuser runs init.sql and the migrations. migrations/001
-- narrows dinesafe_migrator's grants above to what the data pipeline needs.
ALTER DEFAULT PRIVILEGES FOR ROLE CURRENT_USER, dinesafe_migrator
    IN SCHEMA public
    GRANT SELECT ON TABLES TO dinesafe_app;
