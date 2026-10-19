# Deploy to prod

This guide releases a new version to `https://dinesafeviz.com`. Prod only
runs `v*` tags. Release a commit on `main` only after it has been deployed
and checked on stg.

For each release you:

1. Tag the commit, which makes `ci.yml` build the version's images and
   publish the draft release.
2. Snapshot the prod OS disk, so you can restore the VM if the deploy
   damages it.
3. Run `deploy.sh prod vX.Y.Z` on the VM.

## Prerequisites

- `vm01-dsv-prod01` exists and is set up. See
  [Create the prod VM](../initial-setup/create-prod-vm.md).
- `deploy/prod.env` exists on the VM. If it doesn't, run
  `cp deploy/prod.env-example deploy/prod.env` in `~/DineSafeViz`.
- `kv-dsv-prod01` holds the real Cloudflare tunnel token in
  `dsv-tunnel-token`. Without it, the deploy fails its tunnel check.
- The commit you're releasing is running on stg and works there.

## 1. Tag the release

Pick the next version from the draft release that Release Drafter keeps up
to date:

```bash
gh release list --limit 3
```

Tag the tip of `main` and push the tag:

```bash
git switch main && git pull
git tag v0.5.0
git push origin v0.5.0
gh run watch    # wait for ci.yml on v0.5.0
```

`ci.yml` lints, tests, builds, and scans the images, pushes them to GHCR as
`0.5.0` and `0.5`, and publishes the draft release. If any check fails,
nothing is pushed and the release stays a draft. Fix the problem on `main`
and tag a new patch version; don't move a pushed tag.

## 2. Snapshot the prod OS disk

On your workstation, as `dsv-ops01`, take an incremental snapshot of the OS
disk. It goes in `rg-dsv-prod01-snapshots`, which has no lock, so you can
delete old snapshots:

```bash
SUB_ID=a3c53ab4-7208-4b24-bddb-2118dd7b2206   # sub-dsv-prod01
VERSION=v0.5.0
DISK=$(az vm show -g rg-dsv-prod01 -n vm01-dsv-prod01 --subscription "$SUB_ID" \
  --query storageProfile.osDisk.managedDisk.id -o tsv)
az snapshot create -g rg-dsv-prod01-snapshots --subscription "$SUB_ID" \
  -n "snap-dsv-prod01-$VERSION-$(date +%Y%m%d)" --source "$DISK" --incremental true \
  --tags workload=dsv env=prod owner=dsv-admin01 managed-by=manual -o table
```

Keep the newest three snapshots. List them oldest first, then delete all
but the last three:

```bash
az snapshot list -g rg-dsv-prod01-snapshots --subscription "$SUB_ID" \
  --query "sort_by([], &timeCreated)[].[timeCreated, name]" -o tsv
az snapshot delete -g rg-dsv-prod01-snapshots --subscription "$SUB_ID" -n <old-snapshot>
```

`create-prod-vm.sh` restores the OS disk from the newest of these if the
disk is ever missing.

## 3. Deploy

Connect to the VM and run the deploy:

```bash
ssh vm01-dsv-prod01
cd ~/DineSafeViz && ./scripts/deploy.sh prod v0.5.0
```

You don't need to pull first. The script:

1. Fetches the tags and resolves `v0.5.0` to its commit.
2. Stops before changing anything if the `0.5.0` images aren't in GHCR, or
   if the checkout has local changes.
3. Checks out the tag, writes `.env` from `deploy/prod.env` and
   `kv-dsv-prod01`, pulls the images, and starts the stack.
4. Applies the migrations and loads the newest data from `stdsvprod01`.
5. Checks that nginx reaches the app, that containers can't reach the
   instance metadata service, and that the tunnel is connected.

It ends with `deploy: prod is running 0.5.0 (<commit>)`.

<!-- prettier-ignore -->
> [!TIP]
> Run the deploy in `tmux` so a dropped SSH connection doesn't hide the
> result.

On a brand-new environment, Blob Storage is empty, so the deploy stops with
`the data load failed and the site has an empty database`. Fill it from
Toronto Open Data, then rerun the deploy:

```bash
./scripts/pipeline.sh prod ingest
./scripts/deploy.sh prod v0.5.0
```

## 4. Verify

1.  Open `https://dinesafeviz.com` and confirm that the map loads with
    inspection data.
2.  Open `https://dinesafeviz.com/analytics/` and confirm that Grafana
    loads.
3.  On the VM, confirm the data refresh timer is scheduled:

    ```bash
    systemctl list-timers dsv-pipeline.timer
    ```

## Roll back

If the release misbehaves, deploy the previous tag. Its images and Git tag
still exist:

```bash
ssh vm01-dsv-prod01
cd ~/DineSafeViz && ./scripts/deploy.sh prod v0.4.0
```

If the VM itself is damaged, restore it from the snapshot you took in step
2. As `dsv-admin01`, delete the VM and its disk, then attach a disk restored
from the newest snapshot:

1.  Run `bash infra/az/delete-prod-vm.sh` (not `--purge`, which deletes the
    snapshots too). See [Delete the prod VM](../initial-setup/delete-prod-vm.md).
2.  Delete the damaged disk:
    `az disk delete -g rg-dsv-prod01 -n osdisk-vm01-dsv-prod01 --subscription "$SUB_ID"`.
3.  Run `bash infra/az/create-prod-vm.sh`. With no disk, it creates one from
    the newest snapshot and attaches it. See
    [Create the prod VM](../initial-setup/create-prod-vm.md).

## Troubleshoot

| Error or symptom | Fix |
| --- | --- |
| `usage: deploy.sh stg main \| deploy.sh prod vX.Y.Z ...` | Prod needs a full `vX.Y.Z` tag, for example `v0.5.0`. |
| `tag v0.5.0 doesn't exist` | Push the tag (step 1). |
| `... isn't published. Wait for the CI workflow (ci.yml) to finish, then rerun.` | `ci.yml` is still running on the tag, or failed. Check `gh run list --branch v0.5.0`. |
| `deploy/prod.env is missing` | Run `cp deploy/prod.env-example deploy/prod.env` on the VM. |
| `the checkout has local changes` | On the VM, run `git status`, then discard the changes. |
| `pipeline: recent/ is empty` | Run `./scripts/pipeline.sh prod ingest`, then rerun the deploy. |
| `pipeline: historical/ has no complete folder` | Run `./scripts/pipeline.sh prod ingest --historical`, then rerun the deploy. |
| `a container reached IMDS` | Run `sudo systemctl restart dsv-imds-block`, then rerun the deploy. |
| The deploy fails with `dsv-tunnel` logs | Check that `dsv-tunnel-token` in `kv-dsv-prod01` is the prod tunnel's token. |
| SSH times out | Your home IP changed. See [Troubleshoot: your home IP address changed](../../../docs/how-to/azure-vm/troubleshoot-home-ip-change.md). |
