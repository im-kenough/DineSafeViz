# Set up an Azure environment

This checklist lists everything you create and configure to deploy
DineSafeViz to a new environment (`stg` or `prod`). Work through it in order,
once per environment.

- Detailed portal and CLI steps are in the
  [Azure checklist](../../../docs/how-to/azure-vm/azure-checklist.md).
- Resource names and purposes are in [Azure resources](../../ref/6-azure-resources.md).

## 1. Domain names

The domain is registered once and shared by both environments.

- [ ] Register `dinesafeviz.com`.
- [ ] Add the domain to Cloudflare as a zone (Free plan).
- [ ] At the registrar, point the nameservers at the two Cloudflare
      nameservers.
- [ ] Confirm the zone shows **Active** in Cloudflare.

## 2. DNS and zone settings

Cloudflare serves DNS and TLS for both hostnames. Zone settings are set once.

- [ ] Delete any `A` or `CNAME` record on the apex (prod) or `stg` (stg)
      before routing the tunnel; the tunnel creates its own.
- [ ] **SSL/TLS** > **Edge Certificates**: minimum TLS 1.3, **Always Use
      HTTPS**, **Automatic HTTPS Rewrites**.
- [ ] Turn on **Bot fight mode** and confirm the **Cloudflare Free Managed
      Ruleset** is on.
- [ ] Turn on HSTS (6 months, include subdomains) only after both hostnames
      work over HTTPS.

## 3. Cloudflare tunnel

Each environment has its own tunnel. The VM connects out, so no inbound web
port is open.

- [ ] Create tunnel `tun-dsv-<env>01` (**Cloudflared**, **Docker**); copy
      only the token.
- [ ] Add a published application route: `stg.dinesafeviz.com` (stg) or
      `dinesafeviz.com` (prod) to `http://dsv-nginx:80`.
- [ ] Confirm a proxied `CNAME` to `<tunnel-id>.cfargotunnel.com` exists.
- [ ] Store the token as `dsv-tunnel-token` in the vault (step 4).

## 4. Azure resources

Create these as `dsv-admin01` unless noted. See
[Azure resources](../../ref/6-azure-resources.md) for every name.

- [ ] **Subscription:** create or rename `sub-dsv-<env>01`.
- [ ] **Subscription prereqs (admin only):** register `Microsoft.Compute`,
      `Microsoft.Storage`, and `Microsoft.Quota`; raise the Basv2 vCPU quota.
- [ ] **Budget:** `budget-dsv-<env>01-monthly`.
- [ ] **Entra group:** `sg-dsv-<env>01-operators` with its role assignments.
- [ ] **Resource groups:** `rg-dsv-<env>01` (and `rg-dsv-prod01-snapshots`
      for prod), tagged.
- [ ] **Managed identity:** `id-dsv-<env>01-vm`.
- [ ] **Network:** NSG with `AllowSshFromHome`, VNet, subnet with Key Vault
      and Storage service endpoints, public IP, NIC.
- [ ] **Key Vault:** `kv-dsv-<env>01` with purge protection, firewall, and
      roles for the identity and operators.
- [ ] **Secrets (as `dsv-ops01`):** the four generated passwords plus
      `dsv-tunnel-token`.
- [ ] **Storage:** `stdsv<env>01` and the `dinesafe` container, with
      versioning, soft delete, and the identity's data role.
- [ ] **Maintenance configuration:** `mc-dsv-<env>01-vms01`.
- [ ] **VM:** `vm01-dsv-<env>01` on the existing NIC, enrolled in the
      maintenance configuration (`infra/az/create-stg-vm.sh` for stg).
- [ ] **Prod only:** VM Contributor on the VM for the prod operators.
- [ ] Optional: record the state with `infra/az/dump-az-config.sh`.

<!-- prettier-ignore -->
> [!TIP]
> `infra/az/setup-az-vms.sh infra` (as `dsv-admin01`) and
> `infra/az/setup-az-vms.sh secrets` (as `dsv-ops01`) script most of the
> resource group, network, identity, and vault steps.

## 5. Source and images

The VM clones the repo over SSH and pulls public images from GHCR.

- [ ] Create a read-only GitHub deploy key and save the private key as
      `~/.ssh/dsv-deploy-key-RO` on your workstation.
- [ ] Create the VM admin SSH key `~/.ssh/id_ed25519_dsv_<env>01_az_admin`.
- [ ] Confirm `ci.yml` has published `dsv-app` and `dsv-pipeline` to GHCR.
- [ ] Make both GHCR packages public (one-time; can't be undone).

## 6. First deploy

These steps run on the VM. Details are in
[Deploy the stg VM](deploy-stg-vm.md) and
[Deploy the app to prod](deploy-prod-vm.md).

- [ ] SSH in and clone the repo.
- [ ] Run `infra/az/setup-vm.sh`, then open a new SSH session.
- [ ] Copy `deploy/<env>.env-example` to `deploy/<env>.env`.
- [ ] New environment only: run `./scripts/pipeline.sh <env> ingest` to fill
      Blob Storage.
- [ ] Run `./scripts/deploy.sh <env> main` and check `docker compose ps`.
- [ ] Reboot and confirm the stack comes back and the site loads.
- [ ] Prod only: take a snapshot and test a restore before go-live.
- [ ] Add the resource locks.
