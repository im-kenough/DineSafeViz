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

# Prints a token for resource $1 (URL-encoded) from IMDS, as the VM's managed
# identity.
imds_token() {
  curl -sS --fail-with-body --max-time 5 -H Metadata:true \
    "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=$1" \
    | jq -r .access_token \
    || die "can't get a token from IMDS. Run this on the Azure VM, with its managed identity attached."
}
