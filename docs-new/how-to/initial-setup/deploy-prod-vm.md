# Deploy the app to prod

This guide deploys a release to `vm01-dsv-prod01`, which serves
`dinesafeviz.com`. Prod only runs `vX.Y.Z` tags that you've already checked
on stg.

- Part 1 is a one-time VM setup. Skip it if the VM already serves the site.
- Parts 2 to 4 run for every release.
- Resource names are in [Azure resources](../../ref/6-azure-resources.md).

## Before you begin

Everything in
[Set up an Azure environment](setup-azure-environment.md) must be done for
prod.

- [ ] `kv-dsv-prod01` has all five secrets, including `dsv-tunnel-token`.
- [ ] The tunnel `tun-dsv-prod01` routes `dinesafeviz.com` to
      `http://dsv-nginx:80`.
- [ ] Your home IP address is allowed by `nsg-dsv-prod01-app`, the vault, and
      the storage account.
- [ ] The release commit is deployed and working on stg
      ([Deploy the stg VM](deploy-stg-vm.md)).

## 1. Set up the VM (first time only)

These steps prepare a new prod VM. They run on the VM as `dsv-vm-admin`.

1. SSH in. If `~/.ssh/config` has no `vm01-dsv-prod01` entry, use the
   public IP address of `pip-dsv-prod01`.

   ```bash
   ssh dsv-vm-admin@vm01-dsv-prod01
   ```

2. Clone the repo with the deploy key.

   ```bash
   git clone git@github.com:im-kenough/DineSafeViz.git
   cd DineSafeViz
   ```

3. Point the setup script at prod, run it, then restore the file.

   ```bash
   sed -i 's/kv-dsv-stg01/kv-dsv-prod01/; s/@ENV@|stg|/@ENV@|prod|/' \
     infra/az/init-setup-vm.sh
   bash infra/az/setup-vm.sh
   git checkout -- infra/az/init-setup-vm.sh
   ```

<!-- prettier-ignore -->
> [!WARNING]
> `init-setup-vm.sh` hardcodes `kv-dsv-stg01` and the `stg` refresh timer.
> Without the `sed`, its vault check fails on prod and stops the setup
> before hardening. Restore the file afterward: `deploy.sh` refuses to run
> on a checkout with local changes.
> If `setup-vm.sh` exits with an error, restore the file before retrying:
> ```bash
> git checkout -- infra/az/init-setup-vm.sh
> ```

4. Open a new SSH session before closing the old one, to confirm the hardened
   SSH settings and pick up `docker` group membership.
5. Confirm the refresh timer targets prod.

   ```bash
   systemctl cat dsv-pipeline.service | grep -i prod
   systemctl list-timers dsv-pipeline.timer
   ```

6. Create the settings file.

   ```bash
   cp deploy/prod.env-example deploy/prod.env
   ```

7. New environment only: fill Blob Storage from Toronto Open Data.

   ```bash
   ./scripts/pipeline.sh prod ingest
   ```

## 2. Tag the release

This step runs on your workstation. CI builds the `X.Y.Z` images and
publishes the draft release once they're in GHCR.

1. Tag the commit you tested on stg and push the tag.

   ```bash
   git switch main && git pull
   git tag v0.5.0 && git push origin v0.5.0
   gh run watch
   ```

2. Confirm the run passed and the release is no longer a draft.

## 3. Take a snapshot

Take a snapshot before every deploy so you can restore the VM. Run this on
your workstation as `dsv-ops01`.

1. Snapshot the OS disk.

   ```bash
   SUB_ID=a3c53ab4-7208-4b24-bddb-2118dd7b2206   # sub-dsv-prod01
   DISK=$(az vm show -g rg-dsv-prod01 -n vm01-dsv-prod01 \
     --subscription "$SUB_ID" --query storageProfile.osDisk.managedDisk.id -o tsv)
   az snapshot create -g rg-dsv-prod01-snapshots --subscription "$SUB_ID" \
     -n "snap-dsv-prod01-$(date +%Y%m%d-%H%M)" --source "$DISK" \
     --incremental true -o none
   ```

2. Keep the newest three snapshots.

   ```bash
   az snapshot list -g rg-dsv-prod01-snapshots --subscription "$SUB_ID" \
     --query "sort_by(@, &timeCreated)[:-3].id" -o tsv \
     | xargs -r az snapshot delete --ids
   ```

## 4. Deploy

`deploy.sh` checks that the images exist, checks out the tag, writes `.env`
from Key Vault, starts the stack, migrates, loads data, and smoke-tests the
tunnel.

1. Run the deploy on the VM.

   ```bash
   ssh dsv-vm-admin@vm01-dsv-prod01
   cd ~/DineSafeViz && ./scripts/deploy.sh prod v0.5.0
   ```

2. Check the result.
   - The script ends with `deploy: prod is running 0.5.0 (<commit>)`.
   - `docker compose ps` shows every service as healthy.
   - `https://dinesafeviz.com` and `https://dinesafeviz.com/analytics/` load.
3. First deploy only:
   - Reboot (`sudo reboot`) and confirm the stack comes back.
   - Test a restore from the snapshot (Azure checklist, step 8.3).
   - Add `lock-rg-dsv-prod01` (Azure checklist, step 6.6).

## Roll back

If a release misbehaves, deploy the previous tag. Its images and Git tag
still exist.

```bash
cd ~/DineSafeViz && ./scripts/deploy.sh prod v0.4.0
```

- If the VM itself is damaged, restore the snapshot from step 3 instead.

## Next steps

- [Azure checklist](../../../docs/how-to/azure-vm/azure-checklist.md):
  snapshot restore, locks, and secret rotation runbooks.
- [CI and CD](../../../docs/explanation/azure-vm/ci-cd.md): how tags become
  images and releases.
