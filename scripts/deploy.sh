#!/usr/bin/env bash
# Deploys DineSafeViz on its Azure VM, or on your workstation.
#
# Usage: scripts/deploy.sh stg main
#        scripts/deploy.sh prod vX.Y.Z
#        scripts/deploy.sh dev
#
# stg and prod: resolves the ref to a commit, confirms that commit's images
# are in GHCR, checks it out, writes .env from Key Vault, pulls and starts
# the stack, then runs the database migrations and loads the newest data
# from the Blob raw zone. Deploys never contact Toronto Open Data.
# dev: deploys the working tree as it is. Writes .env from deploy/dev.env,
# builds and starts the stack on http://localhost:8080, then migrates and
# loads from stg's raw zone (needs az login).
# Exits non-zero, with the failing services' logs printed last, if anything
# goes wrong. Everything runs inside main() so bash reads the whole script
# before the checkout can replace this file.
set -euo pipefail

usage() {
  echo "usage: deploy.sh stg main | deploy.sh prod vX.Y.Z | deploy.sh dev" >&2
  exit 2
}

die() {
  echo "deploy: $*" >&2
  exit 1
}

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# Prints the stack's state, then the logs of every failed service plus any
# services named as arguments, and exits 1.
fail() {
  echo "deploy: FAILED. Current state:" >&2
  docker compose ps -a >&2 || true
  local failed svc
  failed=$(docker compose ps -a --format json 2>/dev/null \
    | jq -r 'if type == "array" then .[] else . end
             | select(.Health == "unhealthy" or .State == "restarting"
                      or (.State == "exited" and .ExitCode != 0))
             | .Service' 2>/dev/null) || true
  for svc in $failed "$@"; do
    echo "----- logs: $svc -----" >&2
    docker compose logs --no-color --tail 50 "$svc" >&2 || true
  done
  exit 1
}

# Starts the stack with `up $1` (--build or --no-build), waits for the
# long-running services named after $1 to be healthy, and smoke-tests nginx.
start_stack() {
  local up_flag=$1
  shift
  docker compose up -d "$up_flag" --remove-orphans || fail
  docker compose up -d --no-build --wait --wait-timeout 600 "$@" || fail
  docker compose exec -T dsv-nginx wget -q -O /dev/null http://127.0.0.1/healthz \
    || fail dsv-nginx dsv-app
}

# Applies every migration as the database superuser, then loads the newest
# raw-zone data (scripts/pipeline.sh <env> load). Migrations are idempotent.
# A failed load keeps the site up on the data it has, unless there's none.
load_data() {
  local env_name=$1 migration has_rows
  for migration in src/dsv-db/migrations/*.sql; do
    docker compose exec -T dsv-db sh -c \
      'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <"$migration" \
      || fail dsv-db
  done
  if scripts/pipeline.sh "$env_name" load; then
    return
  fi
  has_rows=$(docker compose exec -T dsv-db sh -c \
    'psql -tA -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT EXISTS (SELECT 1 FROM inspections)"') \
    || has_rows=f
  [[ $has_rows == t ]] \
    || die "the data load failed and the site has an empty database. Fix the error above, then rerun."
  echo "deploy: warning: the data load failed; serving the data already in the database" >&2
}

# Writes .env, builds and starts the stack, then loads stg's raw zone.
deploy_dev() {
  scripts/fetch-secrets.sh dev
  start_stack --build dsv-nginx dsv-app dsv-db dsv-analytics
  load_data dev
  echo "deploy: dev is running on http://localhost:8080"
}

main() {
  local env_name=${1:-} ref=${2:-}
  case "$env_name:$ref" in
    dev:) ;;
    stg:main) ;;
    prod:v*) [[ $ref =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || usage ;;
    *) usage ;;
  esac

  local repo_dir
  repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
  cd "$repo_dir"
  require_settings "deploy/$env_name.env" "$env_name"
  if [[ $env_name == dev ]]; then
    deploy_dev
    return
  fi

  # 1. Resolve the ref to a commit and image tag without changing anything.
  local commit tag dirty
  git fetch --quiet --prune --tags --force origin
  # Local edits that don't conflict with the target commit would survive the
  # checkout and run under the new version's name. .env files are ignored.
  dirty=$(git status --porcelain --untracked-files=no)
  [[ -z $dirty ]] \
    || die "the checkout has local changes. Commit, stash, or discard them, then rerun:
$dirty"
  if [[ $env_name == stg ]]; then
    commit=$(git rev-parse --verify --quiet "origin/main^{commit}") \
      || die "can't resolve origin/main"
    tag="sha-${commit:0:7}"
  else
    commit=$(git rev-parse --verify --quiet "refs/tags/$ref^{commit}") \
      || die "tag $ref doesn't exist"
    tag=${ref#v}
  fi

  # 2. Stop before changing anything if the images aren't published yet.
  local image
  for image in dsv-app dsv-init-db; do
    docker manifest inspect "ghcr.io/im-kenough/$image:$tag" >/dev/null 2>&1 \
      || die "ghcr.io/im-kenough/$image:$tag isn't published. Wait for images.yml to finish, then rerun."
  done

  # 3. Check out the code that matches the images.
  git checkout --quiet --detach "$commit" \
    || die "git checkout failed. Fix the working tree on the VM, then rerun."

  # 4. Write .env from Key Vault, pinned to this image tag.
  DSV_VERSION="$tag" "$repo_dir/scripts/fetch-secrets.sh" "$env_name"

  # 5. Pull (including the pipeline image, which is in a profile), start and
  # wait for health, then migrate and load.
  docker compose --profile pipeline pull --quiet
  start_stack --no-build dsv-tunnel dsv-nginx dsv-app dsv-db dsv-analytics
  load_data "$env_name"

  # 6. Smoke test: start_stack checked nginx reaches the app; check the VM's
  # network isolation and that the tunnel is connected.
  # Containers must not reach IMDS (dsv-imds-block.service).
  # IMDS answers 400 without the header and api-version, which wget would
  # report as a failure, so ask properly: success means it's reachable.
  if docker compose exec -T dsv-nginx wget -q -T 3 -O /dev/null --header "Metadata: true" \
      "http://169.254.169.254/metadata/instance?api-version=2021-02-01" 2>/dev/null; then
    die "a container reached IMDS. Run: sudo systemctl restart dsv-imds-block"
  fi
  # cloudflared's /ready returns 200 only while it has a live connection to
  # Cloudflare. (Searching its logs would match old lines, and grep -q on a
  # long log stream fails under pipefail.)
  local tunnel_ready=(docker compose exec -T dsv-nginx wget -q -O /dev/null
    http://dsv-tunnel:2000/ready)
  for _ in {1..14}; do
    "${tunnel_ready[@]}" 2>/dev/null && break
    sleep 2
  done
  "${tunnel_ready[@]}" 2>/dev/null || fail dsv-tunnel

  docker image prune -af >/dev/null
  # No container keeps the pipeline image (compose run --rm), so prune
  # removed it. Pull it back so the timer doesn't depend on GHCR at 07:30.
  docker compose --profile pipeline pull --quiet dsv-pipeline
  echo "deploy: $env_name is running $tag ($commit)"
}

main "$@"
