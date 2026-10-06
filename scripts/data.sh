#!/usr/bin/env bash
# Refreshes the DineSafe CSVs: Toronto Open Data -> Blob -> ./data, and
# optionally loads them into Postgres.
#
# Usage: scripts/data.sh stg|prod [--historical] [--load]   on the VM
#        scripts/data.sh dev [--load]                        on a workstation
#
# On the VM, gets a token for Azure Storage (and nothing else) from IMDS as
# the VM's managed identity, then runs dsv-data fetch and dsv-data sync.
# On dev, gets the token from your az login (dsv-ops01, Blob Data Reader on
# stg) and runs sync only. The account comes from deploy/<env>.env. The token
# reaches the container as a mode-600 file, never as an argument or
# environment variable, and is deleted on exit.
#
# Exit codes: 0 ok, 1 error, 2 usage, 3 fetch failed but the existing Blob
# data was synced (and loaded with --load).
set -euo pipefail

IMDS_URL="http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fstorage.azure.com%2F"

usage() {
  echo "usage: data.sh stg|prod [--historical] [--load] | data.sh dev [--load]" >&2
  exit 2
}

die() {
  echo "data: $*" >&2
  exit 1
}

env_name=${1:-}
[[ $env_name == stg || $env_name == prod || $env_name == dev ]] || usage
shift
historical=() load=
for arg in "$@"; do
  case $arg in
    --historical) [[ $env_name != dev ]] || usage; historical=(--historical) ;;
    --load) load=1 ;;
    *) usage ;;
  esac
done

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"

# dockerd creates a missing ./data as root if compose runs before this script.
mkdir -p data
for dir in data data/dinesafe-historical; do
  [[ ! -e $dir || -w $dir ]] \
    || die "./$dir isn't writable by $(id -un). Run: sudo chown -R $(id -u):$(id -g) data"
done

settings=deploy/$env_name.env
[[ -f $settings ]] \
  || die "$settings is missing. Copy deploy/$env_name.env-example to deploy/$env_name.env first."
# Last assignment wins, as it does when compose reads the copied .env.
account=$(sed -n 's/^DSV_STORAGE_ACCOUNT=//p' "$settings" | tail -n 1)
[[ -n $account ]] || die "DSV_STORAGE_ACCOUNT is missing from $settings"
[[ $account =~ ^[a-z0-9]{3,24}$ ]] \
  || die "DSV_STORAGE_ACCOUNT in $settings isn't a valid storage account name: '$account'"

if [[ $env_name == dev ]]; then
  token=$(az account get-access-token --resource https://storage.azure.com/ \
    --query accessToken -o tsv) \
    || die "can't get a storage token. Run az login as dsv-ops01 first."
else
  token=$(curl -sS --fail-with-body --max-time 5 -H Metadata:true "$IMDS_URL" \
    | jq -r .access_token) \
    || die "can't get a token from IMDS. Run this on the Azure VM, with its managed identity attached."
fi
[[ -n $token && $token != null ]] || die "got an empty storage token"

token_dir=$(mktemp -d)
trap 'rm -rf "$token_dir"' EXIT
(umask 077 && printf '%s' "$token" >"$token_dir/token")

# Runs as you, so ./data stays owned by you.
run_data() {
  docker compose --profile data run --rm --no-deps \
    --user "$(id -u):$(id -g)" \
    -v "$token_dir/token:/run/secrets/storage-token:ro" \
    -e "DSV_STORAGE_ACCOUNT=$account" \
    dsv-data "$@"
}

status=0
if [[ $env_name != dev ]]; then
  if ! run_data fetch "${historical[@]}"; then
    echo "data: fetch failed; continuing with the data already in $account" >&2
    status=3
  fi
fi
run_data sync || die "sync from $account failed; ./data is unchanged"
if [[ -n $load ]]; then
  docker compose run --rm dsv-init-db || die "loading ./data into Postgres failed"
fi
exit "$status"
