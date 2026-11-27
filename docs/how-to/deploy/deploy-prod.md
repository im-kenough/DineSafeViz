# Deploy to prod

Prod only runs `v*` tags. Release a `main` commit only after it works on stg.

## Scripts

- `scripts/deploy.sh`: checks out the tag, confirms its images are in GHCR,
  writes `.env` from Key Vault, starts the stack, migrates and loads data,
  then smoke-tests it. Run it on the VM as `./scripts/deploy.sh prod vX.Y.Z`.
- `scripts/pipeline.sh`: moves data from Toronto Open Data to Blob Storage
  (`ingest`) and from Blob to Postgres (`load`). Run it on the VM as
  `./scripts/pipeline.sh prod ingest` to fill an empty Blob Storage before
  the first deploy.

## Prerequisites

- `vm01-dsv-prod01` is set up, see [Create the prod VM](../initial-setup/create-prod-vm.md).
- `~/DineSafeViz/deploy/prod.env` exists on the VM. If not, copy it from
  `deploy/prod.env-example`.
- `dsv-tunnel-token` in `kv-dsv-prod01` is the real prod tunnel token, see
  [Load the Cloudflare tunnel token](../initial-setup/set-tunnel-token.md).

## 1. Tag the release

```bash
gh release list --limit 3    # next version is on the draft
git switch main && git pull
git tag v0.5.0 && git push origin v0.5.0
gh run watch                 # wait for ci.yml on v0.5.0
```

- `ci.yml` builds and scans the images, pushes `0.5.0` and `0.5` to GHCR,
  and publishes the draft release.
- On failure nothing is pushed. Fix it on `main` and tag a new patch
  version. Don't move a pushed tag.

## 2. Snapshot the OS disk

On your workstation as `dsv-ops01`:

```bash
SUB_ID=a3c53ab4-7208-4b24-bddb-2118dd7b2206   # sub-dsv-prod01
VERSION=v0.5.0
DISK=$(az vm show -g rg-dsv-prod01 -n vm01-dsv-prod01 --subscription "$SUB_ID" \
  --query storageProfile.osDisk.managedDisk.id -o tsv)
az snapshot create -g rg-dsv-prod01-snapshots --subscription "$SUB_ID" \
  -n "snap-dsv-prod01-$VERSION-$(date +%Y%m%d)" --source "$DISK" --incremental true \
  --tags workload=dsv env=prod owner=dsv-admin01 managed-by=manual -o table
```

- Keep the newest three. List them oldest first, then delete the rest:

  ```bash
  az snapshot list -g rg-dsv-prod01-snapshots --subscription "$SUB_ID" \
    --query "sort_by([], &timeCreated)[].[timeCreated, name]" -o tsv
  az snapshot delete -g rg-dsv-prod01-snapshots --subscription "$SUB_ID" -n <old-snapshot>
  ```

- `create-prod-vm.sh` restores from the newest snapshot if the disk is
  missing.

## 3. Deploy

```bash
ssh vm01-dsv-prod01
cd ~/DineSafeViz && ./scripts/deploy.sh prod v0.5.0
```

- No need to pull first, the script fetches the tags.
- It stops before changing anything if the images aren't published or the
  checkout has local changes.
- It ends with `deploy: prod is running 0.5.0 (<commit>)`.
- Run it in `tmux` so a dropped SSH session doesn't hide the result.
- First deploy on an empty Blob Storage fails with
  `the data load failed and the site has an empty database`. Fill it, then
  rerun:

  ```bash
  ./scripts/pipeline.sh prod ingest
  ./scripts/deploy.sh prod v0.5.0
  ```

## 4. Verify

- `https://dinesafeviz.com`: the map loads with inspection data.
- `https://dinesafeviz.com/analytics/`: Grafana loads.
- `systemctl list-timers dsv-pipeline.timer` on the VM shows the next run.

## Roll back

- **Bad release**: deploy the previous tag.

  ```bash
  cd ~/DineSafeViz && ./scripts/deploy.sh prod v0.4.0
  ```

- **Damaged VM**: restore from the step 2 snapshot, as `dsv-admin01`.
  1. `bash infra/az/delete-prod-vm.sh`, not `--purge`, which deletes the
     snapshots too. See [Delete the prod VM](../initial-setup/delete-prod-vm.md).
  2. `az disk delete -g rg-dsv-prod01 -n osdisk-vm01-dsv-prod01 --subscription "$SUB_ID"`
  3. `bash infra/az/create-prod-vm.sh`. With no disk, it restores one from
     the newest snapshot. See [Create the prod VM](../initial-setup/create-prod-vm.md).

## Troubleshoot

| Error | Fix |
| --- | --- |
| `usage: deploy.sh ...` | Use a full `vX.Y.Z` tag. |
| `tag v0.5.0 doesn't exist` | Push the tag (step 1). |
| `... isn't published` | `ci.yml` is still running on the tag, or failed. Check `gh run list --branch v0.5.0`. |
| `deploy/prod.env is missing` | `cp deploy/prod.env-example deploy/prod.env` |
| `the checkout has local changes` | `git status` on the VM, then discard the changes. |
| `pipeline: recent/ is empty` | `./scripts/pipeline.sh prod ingest`, then rerun. |
| `pipeline: historical/ has no complete folder` | `./scripts/pipeline.sh prod ingest --historical`, then rerun. |
| `a container reached IMDS` | `sudo systemctl restart dsv-imds-block`, then rerun. |
| Fails with `dsv-tunnel` logs | Check `dsv-tunnel-token` in `kv-dsv-prod01`. |
| SSH times out | Home IP changed, see [this guide](../../../docs/how-to/azure-vm/troubleshoot-home-ip-change.md). |
