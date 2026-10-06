# Deploy DineSafeViz to stg

This guide takes a freshly created `vm-dsv-stg01` to a running
`https://stg.dinesafeviz.com`, then covers redeploys and tearing the VM down.
It puts the stg-specific steps in order and links to the
[VM setup guide](vm-first-time-setup.md) for the one-time host steps, so you
can follow it from top to bottom in one SSH session.

## Before you begin

The Azure, Cloudflare, and GitHub pieces come from the
[Azure checklist](azure-checklist.md). Confirm each of the following before
you start:

- `vm-dsv-stg01` exists as a `Standard_B2als_v2` (4 GiB), runs Ubuntu 24.04
  LTS, and has `id-dsv-stg01-vm` as its only managed identity (checklist
  steps 3 and 6.3).
- You've run `infra/az/harden-vm.sh` on the VM, and a new SSH login still
  works (checklist step 6.3).
- `kv-dsv-stg01` holds all five secrets, including `dsv-tunnel-token`
  (checklist steps 4.4 and 5.1).
- The storage account `stdsvstg01` exists with its `dinesafe` container,
  firewall, and role assignments. `SUB_ID=<id> ENV=stg01
  infra/az/setup-az-vms.sh infra` creates them.
- The `tun-dsv-stg01` tunnel routes `stg.dinesafeviz.com` to
  `http://dsv-nginx:80` (checklist step 5.2).
- The latest `images.yml` run on `main` is green, and the `dsv-app` and
  `dsv-init-db` GHCR packages are public (checklist step 7.2).

To check the last two items from your workstation, run:

```bash
gh run list --workflow images.yml --branch main -L 1
docker logout ghcr.io
docker manifest inspect ghcr.io/im-kenough/dsv-app:main >/dev/null && echo public
docker manifest inspect ghcr.io/im-kenough/dsv-init-db:main >/dev/null && echo public
```

Each `manifest inspect` prints `public`. If either fails with `unauthorized`,
the package is still private.

## Connect to the VM

The commands in this guide run on the VM as the admin user, `dsv-vm-admin`.
From your workstation, run:

```bash
ssh dsv-vm-admin@vm-dsv-stg01
```

If `vm-dsv-stg01` doesn't resolve from your workstation, use the VM's public
IP address instead. Set `SUB_ID` to the ID of subscription `sub-dsv-stg01`
first:

```bash
ssh dsv-vm-admin@$(az vm show -d -g rg-dsv-stg01 -n vm-dsv-stg01 \
  --subscription "$SUB_ID" --query publicIps -o tsv)
```

The NSG only allows SSH from your home IP address. If the connection times
out, see [Troubleshoot: your home IP address changed](troubleshoot-home-ip-change.md).

<!-- prettier-ignore -->
> [!TIP]
> `deploy.sh` runs for several minutes on a first deploy. Run it in an
> interactive SSH session, or inside `tmux`, so a dropped connection or a
> client-side timeout doesn't hide the result.

## 1. Install Docker Engine and the Compose plugin

The deploy scripts need Docker Engine with the Compose plugin. Ubuntu's own
`docker.io` package doesn't include the plugin, so install from Docker's apt
repository. On the VM, run:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
docker --version && docker compose version
```

The VM never builds images, so this skips `docker-buildx-plugin`.

Source: [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)

## 2. Prepare the host

The host needs the script tools, a swap file, and a firewall rule that keeps
containers away from the instance metadata service. The VM setup guide covers
each one. Run these sections of [the VM setup guide](vm-first-time-setup.md)
in order, then come back here:

1. [Install the tools the scripts need](vm-first-time-setup.md#1-install-the-tools-the-scripts-need).
   Sign out and back in afterward, so `docker` works without `sudo`.
2. [Add a swap file](vm-first-time-setup.md#2-add-a-swap-file).
3. [Clone the repository](vm-first-time-setup.md#3-clone-the-repository).
4. [Block containers from the instance metadata service](vm-first-time-setup.md#4-block-containers-from-the-instance-metadata-service).
   Don't skip the two checks at the end: the container check must print
   `Blocked`, and the host check must print a number.

<!-- prettier-ignore -->
> [!WARNING]
> Don't run a deploy before the metadata block is in place. Without it, any
> container can request a Key Vault token as the VM's identity.

## 3. Set up the checkout

The deploy script runs from the clone and checks out the exact commit it
deploys, so the clone must have no local changes. The clone must be at
`~/DineSafeViz`, the path that
[the VM setup guide](vm-first-time-setup.md#3-clone-the-repository) uses.

1.  Confirm that the clone is clean and tracks GitHub:

    ```bash
    cd ~/DineSafeViz
    git remote get-url origin   # https://github.com/im-kenough/DineSafeViz.git
    git status --short          # prints nothing
    ```

2.  Create the stg settings file from its example. The file holds no secrets
    and is gitignored, so later deploys don't overwrite it. Its
    `DSV_STORAGE_ACCOUNT` names the storage account that holds the CSVs,
    `stdsvstg01`:

    ```bash
    cp deploy/stg.env-example deploy/stg.env
    ```

3.  Check that the VM can read the vault, as described in
    [Check Key Vault access from the VM](vm-first-time-setup.md#5-check-key-vault-access-from-the-vm).
    The output lists the five secret names.

## 4. Deploy

`scripts/deploy.sh stg main` resolves `origin/main` to a commit, confirms its
`sha-<commit>` images exist in GHCR, checks out that commit, writes `.env` from
Key Vault, syncs the CSVs from Blob Storage, then starts the stack and
smoke-tests nginx, the tunnel, and the metadata block. It
stops before changing anything if the images or the vault aren't ready.

```bash
cd ~/DineSafeViz
./scripts/deploy.sh stg main
```

The first deploy takes several minutes. When `stdsvstg01` is empty,
`data.sh` downloads the current and historical CSVs from Toronto Open Data,
validates them, and uploads them before it syncs them into `./data`. Then
`dsv-init-db` loads them into a new database while Grafana runs its schema
migrations. A `403` from `data.sh` right after `setup-az-vms.sh` means the
role assignment hasn't applied yet; wait five minutes and rerun the deploy. Later deploys run the shorter refresh instead. After the
first deploy, schedule the business-day refresh as described in
[Schedule the data refresh](vm-first-time-setup.md#7-schedule-the-data-refresh). The script ends with a line like this:

```text
deploy: stg is running sha-4626289 (4626289...)
```

If it fails, it prints `docker compose ps -a` and the last 50 log lines of
each failed service. See [Troubleshoot a failed deploy](#troubleshoot-a-failed-deploy).

## 5. Verify the deployment

The smoke test only proves that nginx reaches the app and the tunnel is
connected. Check the stack and the site yourself the first time:

1.  On the VM, check the containers and their memory use:

    ```bash
    docker compose ps -a
    docker stats --no-stream
    free -h
    ```

    `dsv-tunnel`, `dsv-nginx`, `dsv-app`, `dsv-db`, and `dsv-analytics` show
    `running` or `healthy`. `dsv-init-db` shows `exited (0)`.

2.  In the Cloudflare dashboard, go to **Networking** > **Tunnels**, and
    confirm that `tun-dsv-stg01` shows **Healthy**.
3.  In a browser, open `https://stg.dinesafeviz.com`. The map loads with
    inspection data.
4.  Open `https://stg.dinesafeviz.com/analytics/`. The Grafana dashboards load
    without a sign-in and show data.

    On the VM, confirm that Grafana uses the PostgreSQL plugin bundled in its
    image:

    ```bash
    docker compose logs dsv-analytics | grep -c 'Skipping loading of plugin'
    ```

    The command prints `0`. For why the bundled plugin matters, see
    [Grafana: the bundled PostgreSQL plugin](../../explanation/grafana-postgres-plugin.md).
5.  Confirm that `https://stg.dinesafeviz.com/analytics/login` returns `404`.
    Admins sign in through an SSH tunnel instead, as described in
    [Sign in to Grafana as admin](vm-first-time-setup.md#sign-in-to-grafana-as-admin).

Optional: reboot once and confirm that everything comes back, as described in
[Confirm the setup survives a reboot](vm-first-time-setup.md#8-confirm-the-setup-survives-a-reboot).

## Redeploy after a merge to main

Each merge to `main` publishes new `sha-<commit>` images. When `images.yml`
is green, rerun the same command on the VM:

```bash
gh run watch                     # on your workstation: wait for images.yml
ssh dsv-vm-admin@vm-dsv-stg01
cd ~/DineSafeViz && ./scripts/deploy.sh stg main
```

You don't need to update the clone first: `deploy.sh` fetches and checks out
the new commit itself. If `images.yml` hasn't finished, the script exits with
`... isn't published. Wait for images.yml to finish, then rerun.`

## Troubleshoot a failed deploy

The deploy script names the failing step. The following table lists the
errors you're most likely to see on a first stg deploy.

| Error or symptom | Cause and fix |
| --- | --- |
| `deploy/stg.env is missing` | Run step 3.2. |
| `the checkout has local changes` | Run `git status`, then commit, stash, or discard the changes. |
| `ghcr.io/im-kenough/...:sha-... isn't published` | `images.yml` is still running or failed, or the package is private. |
| `can't get a token from IMDS` | The identity isn't attached to the VM, or you ran the script inside a container. |
| `can't read ... from kv-dsv-stg01: ForbiddenByFirewall` | The vault firewall doesn't allow the VM's subnet. See checklist step 4.2. |
| `can't read ... from kv-dsv-stg01: ForbiddenByRbac` | `id-dsv-stg01-vm` lacks Key Vault Secrets User, or the role was just assigned. Wait a few minutes. |
| `... must contain only letters, digits, and . _ ~ -` | Regenerate that secret with `openssl rand -hex 32`. See checklist step 4.4. |
| `data: ... HTTP 403` | The storage firewall doesn't allow the VM's subnet, or `id-dsv-stg01-vm` lacks Storage Blob Data Contributor on the `dinesafe` container. Rerun `setup-az-vms.sh infra`, then wait a few minutes. |
| `data: manifest.json isn't in the container` | Blob Storage is empty and the fetch before it failed. Fix the fetch error printed above it, then rerun the deploy. |
| `deploy: warning: using the CSVs already in Blob Storage` | Toronto Open Data failed or its files didn't validate. The deploy continues on the last good data. |
| `a container reached IMDS` | The metadata block isn't in place. Run `sudo systemctl restart dsv-imds-block`, then check its rules as in [the VM setup guide](vm-first-time-setup.md#4-block-containers-from-the-instance-metadata-service). |
| `dsv-init-db` exits non-zero or is `OOMKilled` | Check `free -h` for the swap file, then `docker compose logs dsv-init-db`. |
| `dependency failed to start: container dsv-dsv-analytics-1 is unhealthy` | Grafana's first-start migrations outlasted its health check, so nginx and the tunnel never started. Wait for `docker compose ps` to show `dsv-analytics` as `healthy`, then rerun `deploy.sh`. `docker-compose.vm.yml` allows 300 seconds, so this means the VM is short on memory. Check `free -h`, and confirm the VM is a `Standard_B2als_v2` (checklist step 6.3). |
| Dashboards are empty, and the PostgreSQL data source is missing in Grafana | `dsv-analytics` runs an image without the bundled plugin, such as a `-slim` one. The `backend` network has no internet, so Grafana can't download the plugin. Use the full `grafana/grafana` image in `docker-compose.yml`. See [Grafana: the bundled PostgreSQL plugin](../../explanation/grafana-postgres-plugin.md). |
| `dsv-db` never becomes healthy | `DSV_DB_NAME` must be `dinesafe`. Check `deploy/stg.env`. |
| Smoke test fails on `dsv-tunnel` | The tunnel token is wrong or was rotated. See checklist step 9.3. |
| Site returns `502` but the app is healthy | Run `docker compose restart dsv-nginx`. nginx kept the app's old IP address. |

To read any service's logs after the script exits, run
`docker compose logs --tail 100 <service>` from `~/DineSafeViz`.
The `.env` that `fetch-secrets.sh` writes sets `COMPOSE_FILE`, so plain
`docker compose` commands use the VM override.

## Tear down stg

stg runs on a billed subscription, so delete the VM when you finish testing.
The vault, identity, VNet, NSG, and tunnel stay, and the next stg VM reuses
them. Follow [Delete and recreate the stg VM](azure-checklist.md#95-delete-and-recreate-the-stg-vm).

## Next steps

- Promote a tested commit to prod, as described in
  [Release to prod](../../explanation/azure-vm/ci-cd.md#release-to-prod).
- After a week on stg, revisit the `mem_limit` values in
  `docker-compose.vm.yml` using `docker stats`.
