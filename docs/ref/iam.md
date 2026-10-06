# Identity and access management

This reference lists every identity that can act on the DineSafeViz Azure
deployment: human accounts, security groups, managed identities, and the role
assignments that connect them. Use it to answer "who can do what, where, and
why" without reading the Azure portal.

<!-- prettier-ignore -->
> [!NOTE]
> This describes the target state for the Azure VM deployment. The
> **Status** columns show what exists today. Update them as you create each
> item.

## Principles

Every identity in this document follows the same rules:

- **One purpose per identity.** An identity does one job. Runtime and deploy
  identities are separate, and stg and prod never share an identity.
- **Narrowest scope that works.** Workload roles are granted on a single
  resource or resource group. No workload identity has a subscription-scope
  role.
- **Groups, not users.** Human roles are assigned to Entra security groups.
  Accounts get access through group membership.
- **No standing admin for daily work.** The account with Global Administrator
  is used only for tenant, billing, and RBAC changes.
- **Secrets need an explicit data-plane role.** The vaults use the Azure RBAC
  permission model, so Owner and Contributor don't grant access to secret
  values. Reading or writing secrets requires a Key Vault data-plane role.

## What this document doesn't publish

This repository is public, so the following values are deliberately left out:

- The tenant's primary domain and full user principal names (UPNs).
- Object IDs and client IDs.
- The break-glass account's name. Its random suffix only helps if it stays
  private.

Record those values in your password manager, not in git.

## Naming conventions

Names follow the Cloud Adoption Framework pattern
`<type>-<workload>-<env><instance>[-<purpose>]`.

| Type                         | Prefix | Example                     |
| ---------------------------- | ------ | --------------------------- |
| Human account                | none   | `dsv-ops01`                 |
| Entra security group         | `sg`   | `sg-dsv-prod01-operators`   |
| User-assigned managed identity | `id` | `id-dsv-prod01-vm`          |
| Custom Azure role            | none   | `DSV VM Deployer`           |

Managed identity names end in the **consumer** of the identity (`-vm`,
`-deploy`), not the resource it accesses. The consumer stays the same when its
permissions change; a resource-based suffix such as `-kv` would become wrong
the first time the identity needs a second role.

## Human accounts

The tenant has four human-facing accounts. Only `dsv-ops01` is used for
day-to-day operations.

| Account                | Purpose                                                      | Entra role           | Azure access                                  | Status   |
| ---------------------- | ------------------------------------------------------------ | -------------------- | --------------------------------------------- | -------- |
| `dsv-ops01`            | Daily operator: deploy, rotate secrets, manage the stg VM    | None                 | Through both operator groups                  | Exists  |
| `dsv-admin01`          | "sudo" account: tenant, billing, RBAC, and lock changes only | Global Administrator | Owner at the Tenant Root Group                | Exists   |
| Break-glass (name withheld) | Emergency access if `dsv-admin01` is unavailable        | Global Administrator | Owner at the Tenant Root Group                | Exists   |
| Billing owner (guest MSA) | Original sign-up account; owns the billing account        | None                 | Billing account owner                         | Exists   |

Account rules:

- **`dsv-ops01` has no Entra admin role.** It can't change RBAC, remove resource
  locks, or modify the tenant. Locks (`CanNotDelete`) therefore stop it from
  deleting protected resources.
- **`dsv-admin01` isn't a member of any operator group.** When it needs secret
  access, grant it temporarily and remove the assignment afterward.
- **Home IP changes need different accounts per environment.** `dsv-ops01`
  updates the stg NSG and vault firewall; `dsv-admin01` updates prod. See
  [Troubleshoot: your home IP address changed](../how-to/azure-vm/troubleshoot-home-ip-change.md).
- **All accounts use MFA.** On Entra ID Free, MFA comes from Security Defaults.
- **The break-glass account is cloud-only**, uses the `*.onmicrosoft.com`
  domain, and its credentials are stored offline.

## Security groups

Each environment has one operator group. Membership grants all of that
environment's operator roles.

| Group                     | Members     | Purpose                         | Status  |
| ------------------------- | ----------- | ------------------------------- | ------- |
| `sg-dsv-prod01-operators` | `dsv-ops01` | Operate the prod environment    | Exists  |
| `sg-dsv-stg01-operators`  | `dsv-ops01` | Operate the stg environment     | Exists  |

## Workload identities

Workload identities are user-assigned managed identities. Each one lives in the
resource group of the environment it serves.

| Identity               | Consumer                         | Purpose                                | Phase | Status  |
| ---------------------- | -------------------------------- | -------------------------------------- | ----- | ------- |
| `id-dsv-prod01-vm`     | `vm-dsv-prod01`                  | Read app secrets at deploy time        | 1     | Planned |
| `id-dsv-stg01-vm`      | `vm-dsv-stg01`                   | Read app secrets at deploy time        | 1     | Planned |
| `id-dsv-prod01-deploy` | GitHub Actions, environment `prod` | Run the deploy script on the prod VM | 2     | Planned |
| `id-dsv-stg01-deploy`  | GitHub Actions, environment `stg`  | Run the deploy script on the stg VM  | 2     | Planned |

The `-vm` identities are user-assigned, not system-assigned, because the stg VM
is deleted and recreated for each work cycle. A user-assigned identity keeps its
role assignment across rebuilds; you attach it to each new VM.

## Role assignments

The following table is the complete list of Azure role assignments for the
deployment.

| Principal                 | Role                         | Scope                | Why                                               | Status  |
| ------------------------- | ---------------------------- | -------------------- | ------------------------------------------------- | ------- |
| `id-dsv-prod01-vm`        | Key Vault Secrets User       | `kv-dsv-prod01`      | `fetch-secrets.sh` reads secrets (read-only)      | Planned |
| `id-dsv-stg01-vm`         | Key Vault Secrets User       | `kv-dsv-stg01`       | Same, for stg                                     | Planned |
| `sg-dsv-prod01-operators` | Reader                       | `rg-dsv-prod01`      | See prod resources                                | Exists  |
| `sg-dsv-prod01-operators` | Virtual Machine Contributor  | `vm-dsv-prod01`      | Start, stop, restart, and serial console          | Planned |
| `sg-dsv-prod01-operators` | Disk Snapshot Contributor    | `rg-dsv-prod01-snapshots` | Create and delete pre-deploy snapshots       | Exists  |
| `sg-dsv-prod01-operators` | Key Vault Secrets Officer    | `kv-dsv-prod01`      | Create and rotate prod secrets                    | Planned |
| `sg-dsv-stg01-operators`  | Contributor                  | `rg-dsv-stg01`       | Create and delete the stg VM, disk, NIC, and IP   | Exists  |
| `sg-dsv-stg01-operators`  | Key Vault Secrets Officer    | `kv-dsv-stg01`       | Create and rotate stg secrets                     | Exists  |
| `id-dsv-prod01-deploy`    | DSV VM Deployer (custom)     | `rg-dsv-prod01`      | Phase 2: run deploy, read the OS disk             | Planned |
| `id-dsv-prod01-deploy`    | Disk Snapshot Contributor    | `rg-dsv-prod01-snapshots` | Phase 2: take and prune pre-deploy snapshots | Planned |
| `id-dsv-stg01-deploy`     | DSV VM Deployer (custom)     | `rg-dsv-stg01`       | Phase 2: same, for stg                            | Planned |

Notes on these assignments:

- **Prod operators don't get Contributor.** They can operate the prod VM and its
  secrets, but they can't create, change, or delete prod infrastructure.
  Infrastructure changes go through `dsv-admin01`.
- **Stg operators get Contributor on the stg resource group** because the stg
  VM is rebuilt for every work cycle. Resource locks on the vault, VNet, and
  identity stop those from being deleted.
- **Contributor on `rg-dsv-stg01` doesn't grant secret access.** The vault uses
  RBAC mode, so the separate Key Vault Secrets Officer assignment is still
  required.
- **Prod snapshots live in `rg-dsv-prod01-snapshots`, which has no lock.**
  `rg-dsv-prod01` has a `CanNotDelete` lock, which would also block deleting
  old snapshots. A snapshot can be stored in any resource group in the same
  subscription and region, so pre-deploy snapshots go in the separate,
  unlocked group. Reader on `rg-dsv-prod01` lets operators read the source
  disk. Disk Snapshot Contributor also includes storage account actions; the
  group holds no storage accounts, so they grant nothing in practice.
- **After a vault is recovered from soft delete, recreate its assignments.**
  Soft-deleting a vault deletes its role assignments, and recovery doesn't
  restore them.

## Custom role: DSV VM Deployer

The Phase 2 deploy identities use a custom role instead of Virtual Machine
Contributor. Virtual Machine Contributor also grants
`Microsoft.Compute/virtualMachines/delete`, which a deploy pipeline doesn't
need.

| Action                                               | Why                                   |
| ---------------------------------------------------- | ------------------------------------- |
| `Microsoft.Resources/subscriptions/resourceGroups/read` | Resolve the resource group         |
| `Microsoft.Compute/virtualMachines/read`             | Find the VM and its OS disk           |
| `Microsoft.Compute/virtualMachines/instanceView/read` | Check that the VM is running         |
| `Microsoft.Compute/virtualMachines/runCommand/action` | Run `deploy.sh` on the VM            |
| `Microsoft.Compute/disks/read`                       | Read the OS disk to snapshot it       |

The assignable scopes are `rg-dsv-prod01` and `rg-dsv-stg01`. Snapshot
permissions aren't part of this role; the prod deploy identity gets them from
Disk Snapshot Contributor on `rg-dsv-prod01-snapshots`. Validate the action
list during Phase 2 implementation.

<!-- prettier-ignore -->
> [!IMPORTANT]
> Run Command executes scripts as root on the VM. Anyone who can obtain a
> deploy identity's token effectively has root on that environment's VM. The
> GitHub Environment protections in the next section are what keep that token
> safe.

## GitHub OIDC federated credentials

In Phase 2, GitHub Actions signs in to Azure as a deploy identity without any
stored secret. Each deploy identity has one federated credential that trusts
GitHub's token issuer for one GitHub Environment.

| Identity               | Issuer                                         | Subject                                              | Audience                     |
| ---------------------- | ---------------------------------------------- | ---------------------------------------------------- | ---------------------------- |
| `id-dsv-prod01-deploy` | `https://token.actions.githubusercontent.com`  | `repo:im-kenough/DineSafeViz:environment:prod`       | `api://AzureADTokenExchange` |
| `id-dsv-stg01-deploy`  | `https://token.actions.githubusercontent.com`  | `repo:im-kenough/DineSafeViz:environment:stg`        | `api://AzureADTokenExchange` |

The environment-based subject doesn't include a branch name. Any workflow, on
any branch, that runs a job with `environment: prod` gets a matching token. The
GitHub Environment settings must close that gap:

| GitHub Environment | Deployment branches and tags | Required reviewers |
| ------------------ | ---------------------------- | ------------------ |
| `prod`             | Tags matching `v*` only      | Yes                |
| `stg`              | `main` only                  | No                 |

## Identities outside Azure

These credentials aren't Azure identities, but they grant access to parts of
the deployment.

| Credential                   | Grants                                  | Where it lives                       |
| ---------------------------- | --------------------------------------- | ------------------------------------ |
| `GITHUB_TOKEN`               | Push images to GHCR (`packages: write`) | Issued per workflow run by GitHub    |
| Cloudflare tunnel token (stg) | Run the `tun-dsv-stg01` connector      | `kv-dsv-stg01`, `dsv-tunnel-token`   |
| Cloudflare tunnel token (prod) | Run the `tun-dsv-prod01` connector    | `kv-dsv-prod01`, `dsv-tunnel-token`  |
| VM SSH key                   | Shell access to the VMs                 | Operator's workstation               |
| VM admin password            | Serial console only (SSH password auth is off) | Operator's password manager   |

## Next steps

Create the planned items in this order, and update each **Status** column as
you go:

1. Create `dsv-ops01` and both operator groups, and add `dsv-ops01` to them.
2. Assign the operator roles on resources that already exist
   (`rg-dsv-prod01`, `rg-dsv-stg01`, `kv-dsv-stg01`).
3. Done: create `rg-dsv-prod01-snapshots` without a lock, assign Disk Snapshot
   Contributor there, and remove the earlier assignment on `rg-dsv-prod01`.
4. Create the remaining resources from the Azure checklist, then assign the
   roles on `kv-dsv-prod01`, `vm-dsv-prod01`, and the `-vm` identities.
5. In Phase 2, create the custom role, the deploy identities, and their
   federated credentials.
