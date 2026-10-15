# Helpers shared by the scripts in this directory.

# Prints "<script name>: $*" to stderr and exits 1.
die() {
  local name=${0##*/}
  echo "${name%.sh}: $*" >&2
  exit 1
}

# Prints the value of $2 in env file $1. Last assignment wins, as it does when
# compose reads .env.
setting() {
  sed -n "s/^$2=//p" "$1" | tail -n 1
}

# Prints the value of $2 in env file $1, or dies if it's missing or empty.
require_setting() {
  local value
  value=$(setting "$1" "$2")
  [[ -n $value ]] || die "$2 is missing from $1"
  printf '%s\n' "$value"
}

# Dies unless the settings file $1 for environment $2 exists.
require_settings() {
  [[ -f $1 ]] \
    || die "$1 is missing. Copy deploy/$2.env-example to deploy/$2.env first."
}

# Applies every migration in src/dsv-db/migrations/, in name order, as the
# database superuser inside the running dsv-db. Each one is idempotent, so
# rerunning them is a no-op. Run from the repo root. Returns 1 on the first
# failure.
#
# Each file runs as one transaction (-1), so a load alongside never sees a
# REVOKE without its GRANT, and a failure rolls the whole file back. The
# advisory lock ("DSV@M"; pipeline.py's LOAD_LOCK is a different key) makes
# a deploy and the pipeline timer take turns: concurrent GRANTs on one table
# fail with "tuple concurrently updated".
apply_migrations() {
  local migration
  for migration in src/dsv-db/migrations/*.sql; do
    docker compose exec -T dsv-db sh -c \
      'psql -q -v ON_ERROR_STOP=1 -1 -c "SELECT pg_advisory_xact_lock(293455937613)" -f - -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <"$migration" \
      || return 1
  done
}

# Prints a token for resource $1 (URL-encoded) from IMDS, as the VM's managed
# identity.
imds_token() {
  curl -sS --fail-with-body --max-time 5 -H Metadata:true \
    "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=$1" \
    | jq -r .access_token \
    || die "can't get a token from IMDS. Run this on the Azure VM, with its managed identity attached."
}
