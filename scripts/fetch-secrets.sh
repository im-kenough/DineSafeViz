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
# 600). Nothing is written unless every secret was read. DSV_VERSION comes from the environment
# (scripts/deploy.sh sets it) or is kept from the current .env, so docker
# compose commands keep working after a secret refresh.
set -euo pipefail

IMDS_URL="http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net"

# .env variable=Key Vault secret name
SECRETS=(
  DSV_DB_PASSWORD=dsv-db-password
  DSV_DB_MIGRATOR_PASSWORD=dsv-db-migrator-password
  DSV_DB_APP_PASSWORD=dsv-db-app-password
  DSV_ANALYTICS_ADMIN_PASSWORD=dsv-analytics-admin-password
  DSV_TUNNEL_TOKEN=dsv-tunnel-token
)

die() {
  echo "fetch-secrets: $*" >&2
  exit 1
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
if [[ $env_name == dev ]]; then
  vault=deploy/dev.env
  compose_file=docker-compose.yml
else
  vault=$(sed -n 's/^DSV_KEY_VAULT=//p' "$settings")
  [[ -n $vault ]] || die "DSV_KEY_VAULT is missing from $settings"
  compose_file=docker-compose.yml:docker-compose.vm.yml
  token=$(curl -sS --fail-with-body --max-time 5 -H Metadata:true "$IMDS_URL" \
    | jq -r .access_token) \
    || die "can't get a token from IMDS. Run this on the Azure VM, with its managed identity attached."
fi

# Prints the secret named $2, which .env calls $1.
read_secret() {
  local body reason
  if [[ $env_name == dev ]]; then
    # Last assignment wins, as it does when compose reads .env.
    sed -n "s/^$1=//p" "$settings" | tail -n 1
    return
  fi
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

lines=() secret_vars=()
for pair in "${SECRETS[@]}"; do
  var=${pair%%=*}
  name=${pair#*=}
  # No tunnel locally: dev serves on localhost.
  [[ $env_name == dev && $var == DSV_TUNNEL_TOKEN ]] && continue
  secret_vars+=(-e "^$var=")
  value=$(read_secret "$var" "$name")
  [[ $env_name == dev ]] && name="$var in deploy/dev.env"
  # Values are written single-quoted, so Compose reads them literally.
  if [[ -z $value || $value == *"'"* || $value == *$'\n'* ]]; then
    die "$name is empty or contains a single quote or newline, which .env can't hold"
  fi
  # Generated secrets also end up in URLs (Grafana basic auth), where / @ : #
  # ? % would corrupt them. The tunnel token comes from Cloudflare as base64.
  if [[ $name != dsv-tunnel-token && ! $value =~ ^[A-Za-z0-9._~-]+$ ]]; then
    die "$name must contain only letters, digits, and . _ ~ -. Generate it with: openssl rand -hex 32"
  fi
  lines+=("$var='$value'")
done

version=${DSV_VERSION:-}
if [[ -z $version && -f $repo_dir/.env ]]; then
  version=$(sed -n 's/^DSV_VERSION=//p' "$repo_dir/.env" | tail -n 1)
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
echo "fetch-secrets: wrote .env for $env_name from $vault"
