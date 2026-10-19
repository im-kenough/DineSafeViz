# Create the prod VM

This guide creates `vm01-dsv-prod01` with `infra/az/create-prod-vm.sh`. The
script has two modes:

- **Default (attach)**: brings back the VM that `delete-prod-vm.sh` removed,
  by attaching the kept OS disk `osdisk-vm01-dsv-prod01`. If that disk is
  gone, the script first restores it from the newest snapshot in
  `rg-dsv-prod01-snapshots`. The OS, the clone, and the app data come back as
  they were.
- **`--overwrite`**: deletes the old OS disk (after a prompt) and builds a
  fresh VM from the Ubuntu 24.04 image. Use it for the first build, or when
  you want a clean OS. You then set the VM up as in
  [Set up a fresh VM](#4-set-up-a-fresh-vm).

Either way, the VM reuses `nic-dsv-prod01`, so it keeps the same public IP
address. The script also enrolls the VM in `mc-dsv-prod01-vms01` and gives
`sg-dsv-prod01-operators` Virtual Machine Contributor on it.

<!-- prettier-ignore -->
> [!WARNING]
> A VM built in attach mode has no `osProfile`, so Azure may refuse the patch
> settings that the Sunday schedule needs. The script then warns at the end
> rather than stopping, and the VM may not be patched on schedule. Until
> [#302](https://github.com/im-kenough/DineSafeViz/issues/302) is done, check
> the warning and patch by hand if you get it, or use `--overwrite`.

## Prerequisites

- The prod infrastructure exists: the resource group, NIC, public IP,
  managed identity `id-dsv-prod01-vm`, Key Vault, storage account, and
  maintenance configuration.
- `vm01-dsv-prod01` doesn't exist. To remove it, see
  [Delete the prod VM](delete-prod-vm.md).
- The `az` maintenance extension is installed:
  `az extension add -n maintenance`.
- For `--overwrite`: the admin SSH key
  `~/.ssh/id_ed25519_dsv_prod01_az_admin.pub` and the read-only deploy key
  `~/.ssh/dsv-deploy-key-RO` are on your workstation.

## 1. Sign in as the admin account

Prod operators only have Reader on `rg-dsv-prod01`, so the script refuses to
run as any account other than `dsv-admin01`:

```bash
az login    # dsv-admin01@dinesafevizoutlook.onmicrosoft.com
```

The script selects `sub-dsv-prod01` itself.

## 2. Remove the resource group lock

The script stops if `rg-dsv-prod01` has a lock. If `lock-rg-dsv-prod01`
exists, delete it, and recreate it after step 5:

```bash
az lock list -g rg-dsv-prod01 --subscription a3c53ab4-7208-4b24-bddb-2118dd7b2206 -o table
az lock delete -g rg-dsv-prod01 -n lock-rg-dsv-prod01 \
  --subscription a3c53ab4-7208-4b24-bddb-2118dd7b2206
```

## 3. Run the script

Run it from your clone, because it loads shared helpers from
`infra/az/vm-lib.sh`. Do a dry run first. It checks the prerequisites and
prints the commands without changing anything:

```bash
DRY_RUN=1 bash infra/az/create-prod-vm.sh
bash infra/az/create-prod-vm.sh
```

For a fresh VM, add `--overwrite`:

```bash
DRY_RUN=1 bash infra/az/create-prod-vm.sh --overwrite
bash infra/az/create-prod-vm.sh --overwrite
```

The script adds `Host vm01-dsv-prod01` to `~/.ssh/config`. With
`--overwrite` it also installs the deploy key for the admin user on the VM.

If the script ends with a `WARNING: ... may not be patched on schedule`
message, run the two `az` commands it prints. Then either patch by hand with
`sudo apt update && sudo apt upgrade` after each Sunday, or rebuild with
`--overwrite`.

## 4. Set up a fresh VM

Skip this step in attach mode: the disk already has the setup and the app.

1.  Connect and clone the repository to `~/DineSafeViz`. The data refresh
    timer runs the scripts from this path.

    ```bash
    ssh vm01-dsv-prod01
    git clone git@github.com:im-kenough/DineSafeViz.git ~/DineSafeViz
    cd ~/DineSafeViz
    ```

2.  Run the setup wrapper as the admin user, not with `sudo`. It installs
    Docker, adds swap, blocks containers from the instance metadata service,
    checks Key Vault access, installs the `dsv-pipeline` timer, and hardens
    the OS. It reads `prod` from the hostname.

    ```bash
    bash infra/az/setup-vm.sh
    ```

    When it finishes, open a new SSH session before closing this one. That
    confirms the hardened SSH settings work and picks up your `docker` group
    membership.

3.  Create the prod settings file:

    ```bash
    cp deploy/prod.env-example deploy/prod.env
    ```

4.  Deploy the app as in [Deploy to prod](../deploy/deploy-prod.md). On a
    brand-new environment, Blob Storage is empty, so fill it first:

    ```bash
    ./scripts/pipeline.sh prod ingest
    ```

## 5. Validate

1.  Reboot the VM and confirm the stack comes back up:

    ```bash
    sudo reboot now
    ssh vm01-dsv-prod01
    cd ~/DineSafeViz && docker compose ps
    systemctl list-timers dsv-pipeline.timer
    ```

2.  From your workstation, confirm the maintenance enrollment and patch
    settings:

    ```bash
    az vm show -g rg-dsv-prod01 -n vm01-dsv-prod01 \
      --subscription a3c53ab4-7208-4b24-bddb-2118dd7b2206 \
      --query osProfile.linuxConfiguration.patchSettings
    az maintenance assignment list -g rg-dsv-prod01 \
      --subscription a3c53ab4-7208-4b24-bddb-2118dd7b2206 \
      --provider-name Microsoft.Compute --resource-type virtualMachines \
      --resource-name vm01-dsv-prod01 -o table
    ```

    `patchMode` should be `AutomaticByPlatform` and
    `bypassPlatformSafetyChecksOnUserSchedule` should be `true`. In attach
    mode the first command prints nothing; see the warning at the top.

3.  Open `https://dinesafeviz.com` and confirm that the map loads.

4.  Recreate the resource group lock if you removed it in step 2:

    ```bash
    az lock create -g rg-dsv-prod01 -n lock-rg-dsv-prod01 --lock-type CanNotDelete \
      --subscription a3c53ab4-7208-4b24-bddb-2118dd7b2206
    ```

## Troubleshoot

| Error | Fix |
| --- | --- |
| `signed in as ...; run this as dsv-admin01...` | Run `az login` as `dsv-admin01`. |
| `resource group rg-dsv-prod01 has a lock` | Do step 2. |
| `VM vm01-dsv-prod01 already exists` | Delete it first, see [Delete the prod VM](delete-prod-vm.md). |
| `NIC nic-dsv-prod01 is already attached to ...` | Another VM holds the NIC. Delete that VM, or detach the NIC from it. |
| `no disk osdisk-vm01-dsv-prod01 ... and no snapshot of it` | Nothing to restore. Use `--overwrite`. |
| `az maintenance extension missing` | Run `az extension add -n maintenance`. |
| `can't tell stg from prod by the hostname` (from `setup-vm.sh`) | The VM's hostname isn't `vm01-dsv-prod01`. Check it with `hostname`. |
| SSH times out | Your home IP changed. See [Troubleshoot: your home IP address changed](../../../docs/how-to/azure-vm/troubleshoot-home-ip-change.md). |
