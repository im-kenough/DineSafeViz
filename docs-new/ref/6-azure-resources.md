# Azure resources

This page lists the Azure resources that host DineSafeViz and what each one
is for. Each environment has its own subscription, and both use the same
names, with only the environment suffix changing: `prod01` or `stg01`.

## Naming

Names follow the Cloud Adoption Framework abbreviations, in the form
`<type>-dsv-<env>01[-<purpose>]`.

- `<type>`: the resource type abbreviation, for example `vm`, `nic`, or `kv`.
- `dsv`: the workload, DineSafeViz.
- `<env>01`: the environment, `prod01` or `stg01`.
- Numbered VMs: VMs and their OS disks put the instance number in front, for
  example `vm01-dsv-prod01` and `osdisk-vm01-dsv-prod01`.
- Storage accounts: storage account names can't contain hyphens, so the storage
  account is `stdsv<env>01`.
- Tags: every resource has `workload=dsv`, `env=<prod|stg>`,
  `owner=dsv-admin01`, and `managed-by=manual`.

## Subscriptions and cost

These sit above the resource groups and separate prod billing from stg.

- `sub-dsv-prod01`: the free-account subscription that runs prod 24/7 on the
  free VM and disk allowances.
- `sub-dsv-stg01`: the pay-as-you-go subscription for stg, where the VM
  exists only while you're testing.
- `budget-dsv-prod01-monthly`, `budget-dsv-stg01-monthly`: 40 CAD monthly
  budgets that send alerts at 50, 80, and 100% of actual spend and 100% of
  forecast spend.

## Identity and access

Entra ID accounts and groups separate admin work from daily operations.

- `dsv-admin01`: the cloud-only admin account that creates resources, role
  assignments, and locks.
- `dsv-ops01`: the daily operator account that manages secrets and snapshots
  through the operator groups.
- `sg-dsv-prod01-operators`: lets operators read `rg-dsv-prod01`, manage the
  prod secrets and snapshots, and start, stop, and use the serial console on
  the prod VM.
- `sg-dsv-stg01-operators`: gives stg operators Contributor on
  `rg-dsv-stg01`, plus the stg secrets and read access to the stg CSVs.

## Resource groups

Each environment keeps its resources in one resource group.

- `rg-dsv-prod01`, `rg-dsv-stg01`: hold every resource for the environment
  that's listed below.
- `rg-dsv-prod01-snapshots`: holds the prod OS disk snapshots taken before
  each deploy, with no lock, so old snapshots can be pruned.

## Network

The network gives the VM a fixed address and limits inbound traffic to SSH
from home. Visitors reach the app through the Cloudflare tunnel, not
through an inbound port.

- `vnet-dsv-prod01`, `vnet-dsv-stg01`: the environment's virtual network,
  `10.10.0.0/24` for prod and `10.20.0.0/24` for stg.
- `snet-dsv-prod01-app`, `snet-dsv-stg01-app`: the `/27` subnet for the VM,
  with service endpoints that let it reach Key Vault and Storage privately.
- `nsg-dsv-prod01-app`, `nsg-dsv-stg01-app`: the network security group on
  the subnet, whose only allow rule, `AllowSshFromHome`, admits SSH from your
  home IP address.
- `pip-dsv-prod01`, `pip-dsv-stg01`: the static Standard public IP address
  that gives the VM outbound internet access and your SSH path.
- `nic-dsv-prod01`, `nic-dsv-stg01`: the VM's network interface, which keeps
  the public IP address when the VM is deleted and recreated.

## Compute

The VM runs Ubuntu 24.04 with Docker Compose and pulls the app images from
GHCR.

- `vm01-dsv-prod01`, `vm01-dsv-stg01`: the Trusted Launch VM that runs the
  app containers (`Standard_B2ats_v2` for prod and `Standard_B2als_v2` for
  stg).
- `osdisk-vm01-dsv-prod01`, `osdisk-vm01-dsv-stg01`: the 64 GiB Premium SSD
  OS disk, which prod keeps when its VM is deleted and stg deletes with its
  VM.
- `mc-dsv-prod01-vms01`, `mc-dsv-stg01-vms01`: the Azure Update Manager
  maintenance configuration that patches the VM weekly, on Saturdays for stg
  and Sundays for prod, from midnight Eastern.
- `mc-dsv-prod01-vms01assignment`, `mc-dsv-stg01-vms01assignment`: enroll the
  VM in its maintenance configuration, and are recreated each time the VM is
  rebuilt.

## Identity for the VM

The VM signs in to Azure with a managed identity, so no credentials are
stored on it.

- `id-dsv-prod01-vm`, `id-dsv-stg01-vm`: the VM's user-assigned managed
  identity, which reads the vault secrets and reads and writes the CSV
  container.

## Secrets

The Key Vault keeps the secrets that `scripts/fetch-secrets.sh` reads on the
VM at deploy time.

- `kv-dsv-prod01`, `kv-dsv-stg01`: the Standard, RBAC-model Key Vault with
  purge protection, which only the VM subnet and your home IP address can
  reach.
- `dsv-db-password`: the PostgreSQL superuser password.
- `dsv-db-migrator-password`: the password for the role that runs schema
  migrations.
- `dsv-db-app-password`: the password for the database role that the app's
  services connect as.
- `dsv-analytics-admin-password`: the Grafana admin password.
- `dsv-tunnel-token`: the token that lets `cloudflared` on the VM connect as
  the environment's Cloudflare tunnel.

## Storage

Blob Storage keeps the DineSafe CSVs that the data pipeline loads.

- `stdsvprod01`, `stdsvstg01`: the StorageV2 account with shared keys and
  public access off, which only the VM subnet and your home IP address can
  reach.
- `dinesafe`: the private blob container for the CSVs, with versioning and a
  7-day soft delete so overwritten or deleted files can be recovered.
