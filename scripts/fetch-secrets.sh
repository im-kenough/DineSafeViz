#!/usr/bin/env bash
# Writes .env from deploy/<env>.env and the environment's secrets.
#
# Usage: scripts/fetch-secrets.sh stg|prod   on the Azure VM
#        scripts/fetch-secrets.sh dev        on a workstation
#
# Reads settings from deploy/<env>.env (gitignored; copied from
# deploy/<env>.env-example). On the VM, gets a Key Vault token from
# the instance metadata service (IMDS) as the VM's managed identity, and reads
# each secret with the Key Vault REST API. Dev has no Key Vault or tunnel: its
# throwaway secrets are in deploy/dev.env. Either way, replaces .env (mode
# 600). Nothing is written unless every secret was read. DSV_VERSION comes
# from the environment (scripts/deploy.sh sets it) or is kept from the current
# .env, so docker compose commands keep working after a secret refresh.
set -euo pipefail

IMDS_URL="http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net"

# .env variable=Key Vault secret name
SECRETS=(
  DSV_DB_PASSWORD=dsv-db-password
  DSV_DB_MIGRATOR_PASSWORD=dsv-db-migrator-password
  DSV_DB_APP_PASSWORD=dsv-db-app-password
  DSV_ANALYTICS_ADMIN_PASSWORD=dsv-analytics-admin-password
)

die() {
  echo "fetch-secrets: $*" >&2
  exit 1
}

# Prints the value of $2 in env file $1. Last assignment wins, as it does when
# compose reads .env.
setting() {
  sed -n "s/^$2=//p" "$1" | tail -n 1
}

env_name=${1:-}
if [[ $env_name != stg && $env_name != prod && $env_name != dev ]]; then
  echo "usage: fetch-secrets.sh stg|prod|dev" >&2
  exit 2
fi

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
settings="$repo_dir/deploy/$env_name.env"
[[ -f $settings ]] \
  || die "$settings is missing. Copy deploy/$env_name.env-example to deploy/$env_name.env first."
# read_secret VAR NAME prints the secret that .env calls VAR and Key Vault
# calls NAME; secret_label VAR NAME names it in errors.
if [[ $env_name == dev ]]; then
  source_label=deploy/dev.env
  compose_file=docker-compose.yml
  read_secret() { setting "$settings" "$1"; }
  secret_label() { echo "$1 in deploy/dev.env"; }
else
  vault=$(setting "$settings" DSV_KEY_VAULT)
  [[ -n $vault ]] || die "DSV_KEY_VAULT is missing from $settings"
  source_label=$vault
  compose_file=docker-compose.yml:docker-compose.vm.yml
  # Only the VM runs the tunnel (docker-compose.vm.yml).
  SECRETS+=(DSV_TUNNEL_TOKEN=dsv-tunnel-token)
  token=$(curl -sS --fail-with-body --max-time 5 -H Metadata:true "$IMDS_URL" \
    | jq -r .access_token) \
    || die "can't get a token from IMDS. Run this on the Azure VM, with its managed identity attached."
  read_secret() {
    local body reason
    if body=$(curl -sS --fail-with-body --max-time 10 \
        -H "Authorization: Bearer $token" \
        "https://$vault.vault.azure.net/secrets/$2?api-version=7.4"); then
      jq -r .value <<<"$body"
    else
      reason=$(jq -r '.error.innererror.code // .error.code' <<<"$body" 2>/dev/null) \
        || reason="no response from the vault"
      die "can't read $2 from $vault: $reason"
    fi
  }
  secret_label() { echo "$2"; }
fi

lines=() secret_vars=()
for pair in "${SECRETS[@]}"; do
  var=${pair%%=*}
  name=${pair#*=}
  secret_vars+=(-e "^$var=")
  value=$(read_secret "$var" "$name")
  # Values are written single-quoted, so Compose reads them literally.
  if [[ -z $value || $value == *"'"* || $value == *$'\n'* ]]; then
    die "$(secret_label "$var" "$name") is empty or contains a single quote or newline, which .env can't hold"
  fi
  # Generated secrets stay URL-safe, so one can go into a connection string or
  # basic-auth URL without escaping. The tunnel token comes from Cloudflare as
  # base64.
  if [[ $var != DSV_TUNNEL_TOKEN && ! $value =~ ^[A-Za-z0-9._~-]+$ ]]; then
    die "$(secret_label "$var" "$name") must contain only letters, digits, and . _ ~ -. Generate it with: openssl rand -hex 32"
  fi
  lines+=("$var='$value'")
done

version=${DSV_VERSION:-}
if [[ -z $version && -f $repo_dir/.env ]]; then
  version=$(setting "$repo_dir/.env" DSV_VERSION)
fi

umask 077
tmp=$(mktemp "$repo_dir/.env.XXXXXX")
trap 'rm -f "$tmp"' EXIT
{
  echo "# Written by scripts/fetch-secrets.sh $env_name. Don't edit; rerun the script."
  echo "COMPOSE_FILE=$compose_file"
  # Secrets are left out here and written quoted below.
  grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' "${secret_vars[@]}" "$settings"
  printf '%s\n' "${lines[@]}"
  if [[ -n $version ]]; then
    echo "DSV_VERSION=$version"
  fi
} >"$tmp"
mv "$tmp" "$repo_dir/.env"
trap - EXIT
echo "fetch-secrets: wrote .env for $env_name from $source_label"
