CREATE ROLE dinesafe_migrator WITH LOGIN PASSWORD 'dinesafe_migrator';
CREATE ROLE dinesafe_app      WITH LOGIN PASSWORD 'dinesafe_app';

CREATE TABLE inspections (
    id                          SERIAL PRIMARY KEY,
    establishment_id            TEXT,
    inspection_id               TEXT,
    establishment_name          TEXT,
    establishment_type          TEXT,
    establishment_address       TEXT,
    infraction_details          TEXT,
    inspection_observation      TEXT,
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
    min_inspections_per_year    TEXT
);

GRANT CONNECT ON DATABASE dinesafe TO dinesafe_app;
GRANT USAGE   ON SCHEMA public       TO dinesafe_app;
GRANT SELECT, INSERT, UPDATE ON TABLE inspections TO dinesafe_app;

GRANT CONNECT ON DATABASE dinesafe TO dinesafe_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO dinesafe_migrator;
GRANT ALL PRIVILEGES ON TABLE inspections TO dinesafe_migrator;
GRANT ALL PRIVILEGES ON SEQUENCE inspections_id_seq TO dinesafe_migrator;
