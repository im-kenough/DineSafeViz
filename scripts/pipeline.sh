#!/usr/bin/env bash
# Runs the data pipeline: Toronto Open Data -> Blob raw zone -> Postgres.
#
# Usage: scripts/pipeline.sh stg|prod run|ingest|load [--force] [--historical]
#        scripts/pipeline.sh dev load [--force]
#
#   ingest  Toronto Open Data -> Blob, only if Toronto has newer data
#   load    Blob -> Postgres, only if the newest file isn't loaded yet.
#           Never contacts Toronto Open Data.
#   run     ingest, load, then fail if the newest data is over 10 days old
#   --force ingest: download even if Toronto's data isn't newer.
#           load: reload the newest file even if it's loaded.
#
# On the VM, gets a token for Azure Storage (and nothing else) from IMDS as
# the VM's managed identity. On dev, gets it from your az login (dsv-ops01,
# Blob Data Reader on stg), and can only load. The account comes from
# deploy/<env>.env. The token reaches the container as a mode-600 file,
# never as an argument or environment variable, and is deleted on exit.
#
# Exit codes: 0 ok, 1 error, 2 usage.
set -euo pipefail

usage() {
  echo "usage: pipeline.sh stg|prod run|ingest|load [--force] [--historical] | pipeline.sh dev load [--force]" >&2
  exit 2
}

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

env_name=${1:-}
command=${2:-}
case "$env_name:$command" in
  stg:run | stg:ingest | stg:load | prod:run | prod:ingest | prod:load | dev:load) ;;
  *) usage ;;
esac
shift 2
flags=()
for arg in "$@"; do
  case $arg in
    --force) flags+=(--force) ;;
    --historical) [[ $command != load ]] || usage; flags+=(--historical) ;;
    *) usage ;;
  esac
done

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"

settings=deploy/$env_name.env
require_settings "$settings" "$env_name"
account=$(require_setting "$settings" DSV_STORAGE_ACCOUNT)
[[ $account =~ ^[a-z0-9]{3,24}$ ]] \
  || die "DSV_STORAGE_ACCOUNT in $settings isn't a valid storage account name: '$account'"

if [[ $env_name == dev ]]; then
  token=$(az account get-access-token --resource https://storage.azure.com/ \
    --query accessToken -o tsv) \
    || die "can't get a storage token. Run az login as dsv-ops01 first."
else
  token=$(imds_token https%3A%2F%2Fstorage.azure.com%2F)
fi
[[ -n $token && $token != null ]] || die "got an empty storage token"

token_dir=$(mktemp -d)
trap 'rm -rf "$token_dir"' EXIT
(umask 077 && printf '%s' "$token" >"$token_dir/token")

# dev builds the image from the working tree; the VMs run the image that
# deploy.sh pulled.
build=()
if [[ $env_name == dev ]]; then
  build=(--build)
fi

# Runs as you: the container drops every capability, so root couldn't read
# the mode-600 token file you own. Not exec: the EXIT trap deletes the token.
docker compose --profile pipeline run --rm "${build[@]}" \
  --user "$(id -u):$(id -g)" \
  -v "$token_dir/token:/run/secrets/storage-token:ro" \
  -e "DSV_STORAGE_ACCOUNT=$account" \
  dsv-pipeline "$command" "${flags[@]}" || exit 1
