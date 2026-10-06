#!/usr/bin/env bash
# Writes .env for the Azure VM from Key Vault.
#
# Usage: scripts/fetch-secrets.sh stg|prod
#
# Reads non-secret settings from deploy/<env>.env (gitignored; copied from
# deploy/<env>.env-example), gets a Key Vault token from
# the instance metadata service (IMDS) as the VM's managed identity, reads each
# secret with the Key Vault REST API, and replaces .env (mode 600). Nothing is
# written unless every secret was read. DSV_VERSION comes from the environment
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
if [[ $env_name != stg && $env_name != prod ]]; then
  echo "usage: fetch-secrets.sh stg|prod" >&2
  exit 2
fi

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
settings="$repo_dir/deploy/$env_name.env"
[[ -f $settings ]] \
  || die "$settings is missing. Copy deploy/$env_name.env-example to deploy/$env_name.env first."
vault=$(sed -n 's/^DSV_KEY_VAULT=//p' "$settings")
[[ -n $vault ]] || die "DSV_KEY_VAULT is missing from $settings"

token=$(curl -sS --fail-with-body --max-time 5 -H Metadata:true "$IMDS_URL" \
  | jq -r .access_token) \
  || die "can't get a token from IMDS. Run this on the Azure VM, with its managed identity attached."

read_secret() {
  local body reason
  if body=$(curl -sS --fail-with-body --max-time 10 \
      -H "Authorization: Bearer $token" \
      "https://$vault.vault.azure.net/secrets/$1?api-version=7.4"); then
    jq -r .value <<<"$body"
  else
    reason=$(jq -r '.error.innererror.code // .error.code' <<<"$body" 2>/dev/null) \
      || reason="no response from the vault"
    die "can't read $1 from $vault: $reason"
  fi
}

lines=()
for pair in "${SECRETS[@]}"; do
  var=${pair%%=*}
  name=${pair#*=}
  value=$(read_secret "$name")
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
  echo "COMPOSE_FILE=docker-compose.yml:docker-compose.vm.yml"
  grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' "$settings"
  printf '%s\n' "${lines[@]}"
  if [[ -n $version ]]; then
    echo "DSV_VERSION=$version"
  fi
} >"$tmp"
mv "$tmp" "$repo_dir/.env"
trap - EXIT
echo "fetch-secrets: wrote .env for $env_name from $vault"
