#!/usr/bin/env bash
# Deploys DineSafeViz on its Azure VM.
#
# Usage: scripts/deploy.sh stg main
#        scripts/deploy.sh prod vX.Y.Z
#
# Resolves the ref to a commit, confirms that commit's images are in GHCR,
# checks it out, writes .env from Key Vault, then pulls and starts the stack.
# Exits non-zero, with the failing services' logs printed last, if anything
# goes wrong. Everything runs inside main() so bash reads the whole script
# before the checkout can replace this file.
set -euo pipefail

usage() {
  echo "usage: deploy.sh stg main | deploy.sh prod vX.Y.Z" >&2
  exit 2
}

die() {
  echo "deploy: $*" >&2
  exit 1
}

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

main() {
  local env_name=${1:-} ref=${2:-}
  case "$env_name:$ref" in
    stg:main) ;;
    prod:v*) [[ $ref =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || usage ;;
    *) usage ;;
  esac

  local repo_dir
  repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
  cd "$repo_dir"
  [[ -f deploy/$env_name.env ]] \
    || die "deploy/$env_name.env is missing. Copy deploy/$env_name.env-example to deploy/$env_name.env first."

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

  # 5. Pull and start, wait for the one-shot jobs, then wait for health.
  # `up --wait` can't cover the jobs: it returns while a job still runs, and
  # fails with "exited (0)" if a job finishes before its wait starts. So the
  # jobs get `compose wait` (their exit code), and --wait lists only the
  # long-running services.
  docker compose pull --quiet
  docker compose up -d --no-build --remove-orphans || fail
  docker compose wait dsv-init-db >/dev/null || fail
  docker compose wait dsv-init-analytics >/dev/null || fail
  docker compose up -d --no-build --wait --wait-timeout 600 \
    dsv-tunnel dsv-nginx dsv-app dsv-db dsv-analytics || fail

  # 6. Smoke test: nginx reaches the app, and the tunnel is connected.
  docker compose exec -T dsv-nginx wget -q -O /dev/null http://127.0.0.1/healthz \
    || fail dsv-nginx dsv-app
  # cloudflared's /ready returns 200 only while it has a live connection to
  # Cloudflare. (Searching its logs would match old lines, and grep -q on a
  # long log stream fails under pipefail.)
  local attempt
  for attempt in $(seq 1 15); do
    if docker compose exec -T dsv-nginx wget -q -O /dev/null http://dsv-tunnel:2000/ready \
        2>/dev/null; then
      break
    fi
    if [[ $attempt == 15 ]]; then
      fail dsv-tunnel
    fi
    sleep 2
  done

  docker image prune -af >/dev/null
  echo "deploy: $env_name is running $tag ($commit)"
}

main "$@"
