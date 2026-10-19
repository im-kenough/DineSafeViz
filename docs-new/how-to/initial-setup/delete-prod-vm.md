# Delete the prod VM

This guide deletes `vm01-dsv-prod01` with `infra/az/delete-prod-vm.sh`. The
script has two modes:

- **Default**: deletes the VM only. It keeps the OS disk
  `osdisk-vm01-dsv-prod01` and its snapshots in `rg-dsv-prod01-snapshots`,
  so [Create the prod VM](create-prod-vm.md) can bring the VM back as it was.
  Prod is down until you do.
- **`--purge`**: also deletes the OS disk, any data disks, and every snapshot
  of the OS disk. You can't recover the VM's data afterwards, and the next
  create needs `--overwrite`. If the VM is already gone, `--purge` deletes
  the disk and snapshots that are left.

Both modes keep `nic-dsv-prod01` and `pip-dsv-prod01`, so the next VM gets
the same public IP address. Both also remove the VM's IP address from
`~/.ssh/known_hosts` and its `Host` entry from `~/.ssh/config`.

<!-- prettier-ignore -->
> [!CAUTION]
> Deleting the VM takes `dinesafeviz.com` offline until you create it again.

## 1. Sign in as the admin account

The script refuses to run as any account other than `dsv-admin01`:

```bash
az login    # dsv-admin01@dinesafevizoutlook.onmicrosoft.com
```

The script selects `sub-dsv-prod01` itself.

## 2. Remove the resource group lock

The script stops if `rg-dsv-prod01` has a lock, and with `--purge` it also
checks `rg-dsv-prod01-snapshots`. If `lock-rg-dsv-prod01` exists, delete it:

```bash
az lock list -g rg-dsv-prod01 --subscription a3c53ab4-7208-4b24-bddb-2118dd7b2206 -o table
az lock delete -g rg-dsv-prod01 -n lock-rg-dsv-prod01 \
  --subscription a3c53ab4-7208-4b24-bddb-2118dd7b2206
```

Recreate it after the next create, as in
[Create the prod VM](create-prod-vm.md#5-validate).

## 3. Run the script

Run it from your clone. Do a dry run first. It lists what it would delete and
what it would keep, and changes nothing:

```bash
DRY_RUN=1 bash infra/az/delete-prod-vm.sh
bash infra/az/delete-prod-vm.sh
```

To delete everything, including the disk and snapshots:

```bash
DRY_RUN=1 bash infra/az/delete-prod-vm.sh --purge
bash infra/az/delete-prod-vm.sh --purge
```

The script prints an `About to delete` and a `Keeping` list, then asks you to
confirm. `YES=1` skips the prompt. Before deleting, it sets the delete option
of the disks and NIC to `Detach`, so the VM can't take them with it.

## 4. Confirm what's left

The script ends by listing the resources left in `rg-dsv-prod01`. After a
default delete, the OS disk should still be there and unattached:

```bash
az disk show -g rg-dsv-prod01 -n osdisk-vm01-dsv-prod01 \
  --subscription a3c53ab4-7208-4b24-bddb-2118dd7b2206 \
  --query "{state:diskState, managedBy:managedBy}" -o table
```

`state` should be `Unattached` and `managedBy` empty.

The maintenance assignment `mc-dsv-prod01-vms01assignment` and the operators'
role assignment on the VM go with it. `create-prod-vm.sh` recreates both.

## Troubleshoot

| Error | Fix |
| --- | --- |
| `signed in as ...; run this as dsv-admin01...` | Run `az login` as `dsv-admin01`. |
| `resource group ... has a lock` | Do step 2. For `rg-dsv-prod01-snapshots`, list and delete its lock the same way. |
| `VM vm01-dsv-prod01 not found` | The VM is already deleted. To also delete the disk and snapshots, rerun with `--purge`. |
| `no VM, disk or snapshots left to purge` | Nothing is left to delete. |
