# Azure resources

This page lists every Azure resource for each environment, grouped by
subscription and resource group, with one line on what each one does.

- Names follow `<type>-dsv-<env>01[-<purpose>]`, where `<env>` is `prod` or
  `stg`.
- Storage account names can't contain hyphens, so they're `stdsv<env>01`.
- Every resource has the tags `workload=dsv`, `env=<prod|stg>`,
  `owner=dsv-admin01`, and `managed-by=manual`.
- To set up a new environment, see
  [Set up an Azure environment](../how-to/initial-setup/setup-azure-environment.md).

## Tenant

These Entra ID objects are shared by both environments.

- **Accounts**
  - `dsv-admin01`: cloud-only admin that creates resources, role
    assignments, and locks.
  - `dsv-ops01`: daily operator that manages secrets and snapshots through the
    operator groups.
  - Break-glass account: separate Global Admin used only if `dsv-admin01` is
    locked out.

## Prod

Prod runs 24/7 in the free-account subscription on the free VM and disk
allowances.

- **Subscription `sub-dsv-prod01`**: billing boundary for prod.
  - `budget-dsv-prod01-monthly`: 40 CAD budget that alerts at 50, 80, and 100%
    actual and 100% forecast spend.
  - `sg-dsv-prod01-operators` (Entra group): gives operators Reader on the
    resource group, secrets access, snapshots, and VM start and stop.
  - **Resource group `rg-dsv-prod01`**: holds every prod resource below.
    - **Managed identity**
      - `id-dsv-prod01-vm`: lets the VM read vault secrets and the CSV
        container without stored credentials.
    - **Compute**
      - `vm01-dsv-prod01`: `Standard_B2ats_v2` Ubuntu 24.04 Trusted Launch VM
        that runs the app with Docker Compose.
      - `osdisk-vm01-dsv-prod01`: 64 GiB Premium SSD OS disk, kept when the VM
        is deleted.
      - `mc-dsv-prod01-vms01`: Update Manager maintenance configuration that
        patches the VM Sundays from midnight Eastern.
      - `mc-dsv-prod01-vms01assignment`: enrolls the VM in the maintenance
        configuration.
    - **Network**
      - `vnet-dsv-prod01`: virtual network, `10.10.0.0/24`.
      - `snet-dsv-prod01-app`: `/27` VM subnet with service endpoints for Key
        Vault and Storage.
      - `nsg-dsv-prod01-app`: subnet firewall whose only allow rule admits SSH
        from your home IP address.
      - `pip-dsv-prod01`: static public IP address for outbound traffic and
        SSH.
      - `nic-dsv-prod01`: VM network interface that keeps the public IP address
        across VM rebuilds.
    - **Key Vault**
      - `kv-dsv-prod01`: RBAC-model vault with purge protection, reachable only
        from the VM subnet and your home IP address.
        - `dsv-db-password`: PostgreSQL superuser password.
        - `dsv-db-migrator-password`: password for the schema migration role.
        - `dsv-db-app-password`: password for the role the app connects as.
        - `dsv-analytics-admin-password`: Grafana admin password.
        - `dsv-tunnel-token`: token `cloudflared` uses to connect as the prod
          tunnel.
    - **Storage**
      - `stdsvprod01`: StorageV2 account with shared keys and public access
        off, reachable only from the VM subnet and your home IP address.
        - `dinesafe`: private blob container for the DineSafe CSVs, with
          versioning and 7-day soft delete.
    - **Locks**
      - `lock-rg-dsv-prod01`: `CanNotDelete` lock on the whole resource group
        (to do, after the first deploy works).
  - **Resource group `rg-dsv-prod01-snapshots`**: holds OS disk snapshots,
    with no lock so old ones can be pruned.
    - `snap-dsv-prod01-<yyyymmdd-hhmm>`: incremental OS disk snapshot taken
      before each deploy; keep the newest three.

## Stg

Stg runs in a pay-as-you-go subscription. The VM and its OS disk exist only
while you're testing; everything else persists.

- **Subscription `sub-dsv-stg01`**: billing boundary for stg.
  - `budget-dsv-stg01-monthly`: 40 CAD budget that alerts at 50, 80, and 100%
    actual and 100% forecast spend.
  - `sg-dsv-stg01-operators` (Entra group): gives operators Contributor on the
    resource group, secrets access, and read access to the CSVs.
  - **Resource group `rg-dsv-stg01`**: holds every stg resource below.
    - **Managed identity**
      - `id-dsv-stg01-vm`: lets the VM read vault secrets and the CSV
        container without stored credentials.
    - **Compute (deleted between test sessions)**
      - `vm01-dsv-stg01`: `Standard_B2als_v2` Ubuntu 24.04 Trusted Launch VM
        that runs the app with Docker Compose.
      - `osdisk-vm01-dsv-stg01`: 64 GiB Premium SSD OS disk, deleted with the
        VM.
      - `mc-dsv-stg01-vms01`: Update Manager maintenance configuration that
        patches the VM Saturdays from midnight Eastern.
      - `mc-dsv-stg01-vms01assignment`: enrolls the VM in the maintenance
        configuration; recreated with each VM.
    - **Network**
      - `vnet-dsv-stg01`: virtual network, `10.20.0.0/24`.
      - `snet-dsv-stg01-app`: `/27` VM subnet with service endpoints for Key
        Vault and Storage.
      - `nsg-dsv-stg01-app`: subnet firewall whose only allow rule admits SSH
        from your home IP address.
      - `pip-dsv-stg01`: static public IP address for outbound traffic and SSH.
      - `nic-dsv-stg01`: VM network interface that keeps the public IP address
        across VM rebuilds.
    - **Key Vault**
      - `kv-dsv-stg01`: RBAC-model vault with purge protection, reachable only
        from the VM subnet and your home IP address.
        - `dsv-db-password`: PostgreSQL superuser password.
        - `dsv-db-migrator-password`: password for the schema migration role.
        - `dsv-db-app-password`: password for the role the app connects as.
        - `dsv-analytics-admin-password`: Grafana admin password.
        - `dsv-tunnel-token`: token `cloudflared` uses to connect as the stg
          tunnel.
    - **Storage**
      - `stdsvstg01`: StorageV2 account with shared keys and public access off,
        reachable only from the VM subnet and your home IP address.
        - `dinesafe`: private blob container for the DineSafe CSVs, with
          versioning and 7-day soft delete.
    - **Locks (to do)**
      - `lock-kv-dsv-stg01`: `CanNotDelete` lock on the vault.
      - `lock-vnet-dsv-stg01`: `CanNotDelete` lock on the virtual network.
      - `lock-id-dsv-stg01-vm`: `CanNotDelete` lock on the managed identity.
