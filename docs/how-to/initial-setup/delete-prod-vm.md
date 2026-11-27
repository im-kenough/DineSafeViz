# Delete the prod VM

## Script

- `infra/az/delete-prod-vm.sh`: deletes `vm01-dsv-prod01`, keeps the NIC
  and public IP, and removes the VM from `~/.ssh/known_hosts` and
  `~/.ssh/config`. Run it on your workstation as `dsv-admin01`, with no args
  to keep the OS disk and snapshots, or with `--purge` to delete them too.

## Modes

- **Default**: deletes the VM only.
  - Keeps `osdisk-vm01-dsv-prod01` and its snapshots in
    `rg-dsv-prod01-snapshots`.
  - [Create the prod VM](create-prod-vm.md) brings it back as it was.
- **`--purge`**: also deletes the OS disk, any data disks, and every
  snapshot of the OS disk.
  - Can't be undone. The next create needs `--overwrite`.
  - If the VM is already gone, deletes whatever disk and snapshots are left.

<!-- prettier-ignore -->
> [!CAUTION]
> `dinesafeviz.com` is offline until you create the VM again.

## 1. Sign in as admin

```bash
az login    # dsv-admin01@dinesafevizoutlook.onmicrosoft.com
```

- The script refuses other accounts, and selects `sub-dsv-prod01` itself.

## 2. Remove the RG lock

The script stops if `rg-dsv-prod01` is locked (with `--purge`, also
`rg-dsv-prod01-snapshots`):

```bash
SUB_ID=a3c53ab4-7208-4b24-bddb-2118dd7b2206   # sub-dsv-prod01
az lock list -g rg-dsv-prod01 --subscription "$SUB_ID" -o table
az lock delete -g rg-dsv-prod01 -n lock-rg-dsv-prod01 --subscription "$SUB_ID"
```

- Recreate the lock after the next create, see
  [Create the prod VM](create-prod-vm.md#5-validate).

## 3. Run the script

From your clone. Dry run first, which lists what it would delete and keep
and changes nothing:

```bash
DRY_RUN=1 bash infra/az/delete-prod-vm.sh [--purge]
bash infra/az/delete-prod-vm.sh [--purge]
```

- Prints `About to delete` and `Keeping` lists, then asks you to confirm.
  `YES=1` skips the prompt.
- Sets the disk and NIC delete options to `Detach` before deleting, so the
  VM can't take them with it.

## 4. Confirm what's left

After a default delete, the disk should be `Unattached` with an empty
`managedBy`:

```bash
az disk show -g rg-dsv-prod01 -n osdisk-vm01-dsv-prod01 --subscription "$SUB_ID" \
  --query "{state:diskState, managedBy:managedBy}" -o table
```

- The maintenance assignment and the operators' role on the VM go with it.
  `create-prod-vm.sh` recreates both.

## Troubleshoot

| Error | Fix |
| --- | --- |
| `signed in as ...` | `az login` as `dsv-admin01`. |
| `... has a lock` | Step 2. Use the same commands for `rg-dsv-prod01-snapshots`. |
| `VM ... not found` | Already deleted. Rerun with `--purge` to delete the disk and snapshots too. |
| `no VM, disk or snapshots left to purge` | Nothing left to delete. |
