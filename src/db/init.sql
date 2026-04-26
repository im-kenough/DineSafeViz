-- Create the final inspections table
CREATE TABLE inspections (
    id                     SERIAL PRIMARY KEY,
    establishment_id       TEXT,
    inspection_id          TEXT,
    establishment_name     TEXT,
    establishment_type     TEXT,
    establishment_address  TEXT,
    infraction_details     TEXT,
    inspection_observation TEXT,
    inspection_date        DATE,
    severity               TEXT,
    action                 TEXT,
    outcome                TEXT,
    outcome_date           TEXT,
    amount_fined           TEXT,
    latitude               DOUBLE PRECISION,
    longitude              DOUBLE PRECISION,
    unique_id              TEXT
);

-- Staging table: all TEXT, matches CSV column order exactly (17 columns)
CREATE TABLE _csv_staging (
    _id                    TEXT,
    establishment_id       TEXT,
    inspection_id          TEXT,
    establishment_name     TEXT,
    establishment_type     TEXT,
    establishment_address  TEXT,
    infraction_details     TEXT,
    inspection_observation TEXT,
    inspection_date        TEXT,
    severity               TEXT,
    action                 TEXT,
    outcome                TEXT,
    outcome_date           TEXT,
    amount_fined           TEXT,
    latitude               TEXT,
    longitude              TEXT,
    unique_id              TEXT
);

-- Bulk load CSV (HEADER skips the first line, CSV handles quoted commas and CRLF)
COPY _csv_staging FROM '/data/Dinesafe.csv' WITH (FORMAT csv, HEADER true);

-- Transform into final table, converting 'None'/empty strings to actual NULLs
INSERT INTO inspections (
    establishment_id, inspection_id, establishment_name, establishment_type,
    establishment_address, infraction_details, inspection_observation,
    inspection_date, severity, action, outcome, outcome_date, amount_fined,
    latitude, longitude, unique_id
)
SELECT
    NULLIF(establishment_id, 'None'),
    NULLIF(inspection_id, 'None'),
    NULLIF(establishment_name, 'None'),
    NULLIF(establishment_type, 'None'),
    NULLIF(establishment_address, 'None'),
    NULLIF(infraction_details, 'None'),
    NULLIF(inspection_observation, 'None'),
    NULLIF(inspection_date, 'None')::DATE,
    NULLIF(severity, 'None'),
    NULLIF(action, 'None'),
    NULLIF(outcome, 'None'),
    NULLIF(outcome_date, 'None'),
    NULLIF(NULLIF(amount_fined, 'None'), ''),
    NULLIF(latitude, '')::DOUBLE PRECISION,
    NULLIF(longitude, '')::DOUBLE PRECISION,
    NULLIF(unique_id, 'None')
FROM _csv_staging;

-- Clean up
DROP TABLE _csv_staging;
