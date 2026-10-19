# Create the prod VM

## Scripts

- `infra/az/create-prod-vm.sh`: creates `vm01-dsv-prod01` on the existing
  NIC (same public IP), enrolls it in `mc-dsv-prod01-vms01`, grants
  `sg-dsv-prod01-operators` VM Contributor, and adds it to `~/.ssh/config`.
  Run it on your workstation as `dsv-admin01`, with no args to reattach the
  kept OS disk, or with `--overwrite` to build fresh from the Ubuntu image.
- `infra/az/setup-vm.sh`: sets up a fresh VM by running `init-setup-vm.sh`
  (Docker, swap, IMDS block, Key Vault check, refresh timer) then
  `harden-vm.sh` (OS hardening). Run it on the VM as the admin user, not
  with `sudo`. It reads `prod` from the hostname.

## Modes

- **Default (attach)**: reattaches `osdisk-vm01-dsv-prod01`, or restores it
  from the newest snapshot in `rg-dsv-prod01-snapshots` if it's gone. OS,
  clone, and data come back as they were. No setup needed.
- **`--overwrite`**: deletes the old disk (after a prompt), builds from the
  image, and installs the deploy key. Needs the setup in step 4.

<!-- prettier-ignore -->
> [!WARNING]
> Attach mode has no `osProfile`, so Azure may refuse the patch settings the
> Sunday schedule needs. The script then warns instead of stopping. If you
> get the warning, patch by hand or use `--overwrite` until
> [#302](https://github.com/im-kenough/DineSafeViz/issues/302) is done.

## Prerequisites

- Prod infra exists (RG, NIC, public IP, `id-dsv-prod01-vm`, Key Vault,
  storage, maintenance config).
- `vm01-dsv-prod01` doesn't exist. See [Delete the prod VM](delete-prod-vm.md).
- `az extension add -n maintenance`
- `--overwrite` only: `~/.ssh/id_ed25519_dsv_prod01_az_admin.pub` and
  `~/.ssh/dsv-deploy-key-RO` on your workstation.

## 1. Sign in as admin

```bash
az login    # dsv-admin01@dinesafevizoutlook.onmicrosoft.com
```

- The script refuses other accounts. Prod operators only have Reader on
  the RG.
- It selects `sub-dsv-prod01` itself.

## 2. Remove the RG lock

The script stops if `rg-dsv-prod01` is locked:

```bash
SUB_ID=a3c53ab4-7208-4b24-bddb-2118dd7b2206   # sub-dsv-prod01
az lock list -g rg-dsv-prod01 --subscription "$SUB_ID" -o table
az lock delete -g rg-dsv-prod01 -n lock-rg-dsv-prod01 --subscription "$SUB_ID"
```

## 3. Run the script

From your clone (it sources `infra/az/vm-lib.sh`). Dry run first, which
checks the prerequisites and prints the commands without changing anything:

```bash
DRY_RUN=1 bash infra/az/create-prod-vm.sh [--overwrite]
bash infra/az/create-prod-vm.sh [--overwrite]
```

- On a patching `WARNING`, run the two `az` commands it prints.

## 4. Set up a fresh VM (`--overwrite` only)

```bash
ssh vm01-dsv-prod01
git clone git@github.com:im-kenough/DineSafeViz.git ~/DineSafeViz
cd ~/DineSafeViz
bash infra/az/setup-vm.sh
cp deploy/prod.env-example deploy/prod.env
```

- Clone to `~/DineSafeViz`. The refresh timer runs the scripts from there.
- After `setup-vm.sh`, open a new SSH session before closing the old one.
  This checks the hardened SSH settings and picks up the `docker` group.
- Then deploy, see [Deploy to prod](../deploy/deploy-prod.md).

## 5. Validate

- Reboot, then check the stack and the timer:

  ```bash
  sudo reboot now
  ssh vm01-dsv-prod01
  cd ~/DineSafeViz && docker compose ps
  systemctl list-timers dsv-pipeline.timer
  ```

- From your workstation, check the patch settings and the enrollment:

  ```bash
  az vm show -g rg-dsv-prod01 -n vm01-dsv-prod01 --subscription "$SUB_ID" \
    --query osProfile.linuxConfiguration.patchSettings
  az maintenance assignment list -g rg-dsv-prod01 --subscription "$SUB_ID" \
    --provider-name Microsoft.Compute --resource-type virtualMachines \
    --resource-name vm01-dsv-prod01 -o table
  ```

  - Expect `patchMode: AutomaticByPlatform` and
    `bypassPlatformSafetyChecksOnUserSchedule: true`.
  - In attach mode the first command prints nothing (see the warning).
- Open `https://dinesafeviz.com` and confirm that the map loads.
- Recreate the lock:

  ```bash
  az lock create -g rg-dsv-prod01 -n lock-rg-dsv-prod01 --lock-type CanNotDelete \
    --subscription "$SUB_ID"
  ```

## Troubleshoot

| Error | Fix |
| --- | --- |
| `signed in as ...` | `az login` as `dsv-admin01`. |
| `... has a lock` | Step 2. |
| `VM ... already exists` | [Delete the prod VM](delete-prod-vm.md) first. |
| `NIC ... is already attached to ...` | Delete that VM or detach the NIC. |
| `no disk ... and no snapshot of it` | Use `--overwrite`. |
| `az maintenance extension missing` | `az extension add -n maintenance` |
| `can't tell stg from prod by the hostname` | `setup-vm.sh` ran on a VM not named `vm01-dsv-prod01`. Check `hostname`. |
| SSH times out | Home IP changed, see [this guide](../../../docs/how-to/azure-vm/troubleshoot-home-ip-change.md). |
