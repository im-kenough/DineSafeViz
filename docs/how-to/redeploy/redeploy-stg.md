# Redeploy DineSafeViz to stg

This guide redeploys the app to `https://stg.dinesafeviz.com` after the VM is
already set up. Stg always deploys the latest commit on `main`, using the
images that `images.yml` publishes for that commit. For a first-time setup,
see [Deploy DineSafeViz to stg](../azure-vm/deploy-stg.md).

## Redeploy

Merge your change to `main`, then follow these steps.

1.  On your workstation, wait for the `images.yml` run on `main` to pass:

    ```bash
    gh run watch
    ```

2.  Connect to the VM:

    ```bash
    ssh dsv-vm-admin@vm-dsv-stg01
    ```

3.  On the VM, run the deploy:

    ```bash
    cd ~/DineSafeViz && ./scripts/deploy.sh stg main
    ```

    You don't need to pull first: the script fetches and checks out the new
    commit itself. It ends with a line like
    `deploy: stg is running sha-4626289 (4626289...)`.

4.  Open `https://stg.dinesafeviz.com` and confirm that the map loads.

<!-- prettier-ignore -->
> [!TIP]
> Run the deploy in `tmux` so a dropped SSH connection doesn't hide the
> result.

## Redeploy from a fresh clone

Use this procedure if you deleted the clone, the Docker images, and the
volumes on the VM, but the rest of the host setup is still in place. That
setup includes Docker, the swap file, `dsv-imds-block.service`, and the
`dsv-pipeline` timer. These live outside the clone, so deleting it doesn't
remove them.

1.  On your workstation, wait for the `images.yml` run on `main` to pass, then
    connect to the VM, as in steps 1 and 2 of [Redeploy](#redeploy).

2.  On the VM, confirm that the metadata block is active. The deploy fails
    its smoke test without it.

    ```bash
    systemctl is-active dsv-imds-block    # prints active
    ```

    If it prints anything else, run
    `sudo systemctl enable --now dsv-imds-block`. If the unit doesn't exist,
    install it as in
    [Block containers from the instance metadata service](../azure-vm/vm-first-time-setup.md#4-block-containers-from-the-instance-metadata-service).

3.  Clone the repository to `~/DineSafeViz`. The `dsv-pipeline` unit runs
    the scripts from this path, so it must match:

    ```bash
    git clone https://github.com/im-kenough/DineSafeViz.git ~/DineSafeViz
    cd ~/DineSafeViz
    ```

4.  Recreate the stg settings file. It's gitignored, so the clone doesn't
    include it:

    ```bash
    cp deploy/stg.env-example deploy/stg.env
    ```

5.  Run the deploy:

    ```bash
    ./scripts/deploy.sh stg main
    ```

    With no images or volumes, this takes several minutes. The script pulls
    every image, then starts Postgres and Grafana on new volumes, which use
    the passwords from Key Vault. It then loads all the data from the
    `stdsvstg01` raw zone.

    If the raw zone is empty, for example because you also emptied the
    `dinesafe` container, the deploy stops with
    `pipeline: recent/ is empty` and
    `the data load failed and the site has an empty database`. The stack
    stays up. Download the data from Toronto Open Data into the raw zone,
    then rerun the deploy so it finishes its smoke tests:

    ```bash
    ./scripts/pipeline.sh stg ingest
    ./scripts/deploy.sh stg main
    ```

    `ingest` also downloads the historical data if the raw zone has none,
    which the first load needs.

6.  Confirm that the data refresh timer is still scheduled:

    ```bash
    systemctl list-timers dsv-pipeline.timer
    ```

    If it's missing, or you cloned to a different path, reinstall it as in
    [Schedule the data refresh](../azure-vm/vm-first-time-setup.md#7-schedule-the-data-refresh).

7.  Open `https://stg.dinesafeviz.com` and confirm that the map loads with
    inspection data.

Grafana starts with a new database, so it loses any changes you made in its
UI. The provisioned dashboards and data source come back on their own.

## Troubleshoot

The following table lists the errors you're most likely to see on a
redeploy. For the full list, see
[Troubleshoot a failed deploy](../azure-vm/deploy-stg.md#troubleshoot-a-failed-deploy).

| Error or symptom | Fix |
| --- | --- |
| `... isn't published. Wait for images.yml to finish, then rerun.` | `images.yml` is still running or failed. Wait for it, then rerun. |
| `deploy/stg.env is missing` | Run step 4 of [Redeploy from a fresh clone](#redeploy-from-a-fresh-clone). |
| `the data load failed and the site has an empty database` | The first load failed. Read the `pipeline:` error printed just above it, and fix that error as described in the following rows. |
| `pipeline: recent/ is empty` | The raw zone has no data. Run `./scripts/pipeline.sh stg ingest`, then rerun the deploy. |
| `pipeline: historical/ has no complete folder` | Run `./scripts/pipeline.sh stg ingest --historical`, then rerun the deploy. |
| `pipeline: GET https://stdsvstg01... HTTP 403` | The storage firewall or role assignment blocks the VM. Rerun `setup-az-vms.sh infra` from your workstation, wait a few minutes, then rerun the deploy. |
| `a container reached IMDS` | Run `sudo systemctl restart dsv-imds-block`, then rerun the deploy. |
| `the checkout has local changes` | On the VM, run `git status`, then discard the changes. |
| SSH times out | Your home IP changed. See [Troubleshoot: your home IP address changed](../azure-vm/troubleshoot-home-ip-change.md). |
