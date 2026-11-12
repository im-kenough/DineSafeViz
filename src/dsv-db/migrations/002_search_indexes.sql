-- 002: indexes for restaurant search (/search) and the restaurant page
-- (/establishment/<id>). Like 001, scripts/deploy.sh and scripts/pipeline.sh
-- apply this on every run, so every statement must be idempotent.
--
-- apply_migrations runs each file in one transaction, so CREATE INDEX can't be
-- CONCURRENTLY. The first run takes a few seconds and blocks writes, not
-- reads; the pipeline applies migrations before it loads, so no load is
-- waiting on it. Later runs are no-ops.

-- Ships with the postgres image. Trigram indexes let ILIKE '%word%' skip the
-- full-table scan.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Search matches each word against the name or the address.
CREATE INDEX IF NOT EXISTS inspections_establishment_name_trgm_idx
    ON inspections USING gin (establishment_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS inspections_establishment_address_trgm_idx
    ON inspections USING gin (establishment_address gin_trgm_ops);

-- Search and the restaurant page read all of a restaurant's rows by ID.
CREATE INDEX IF NOT EXISTS inspections_establishment_id_idx
    ON inspections (establishment_id);
