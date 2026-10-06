#!/usr/bin/env bash
# Sets the app and migrator role passwords from the environment.
#
# The Postgres image runs this once, after init.sql, when the data volume is
# empty. Changing a secret later doesn't rerun it: use ALTER ROLE instead
# (see "Rotate a database password" in docs/how-to/azure-vm/azure-checklist.md).
set -euo pipefail

: "${DSV_DB_APP_PASSWORD:?DSV_DB_APP_PASSWORD must be set}"
: "${DSV_DB_MIGRATOR_PASSWORD:?DSV_DB_MIGRATOR_PASSWORD must be set}"

# psql variables (:'name') quote the values, so any character is safe.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_pw="$DSV_DB_APP_PASSWORD" \
  -v migrator_pw="$DSV_DB_MIGRATOR_PASSWORD" <<'EOSQL'
ALTER ROLE dinesafe_app      PASSWORD :'app_pw';
ALTER ROLE dinesafe_migrator PASSWORD :'migrator_pw';
EOSQL
