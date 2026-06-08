# Deploy application

This document provides instructions for deploying the
DineSafeViz application using the IaC toolchain.

**Prerequisites:** Complete the [Install Instructions](docs/how-to/install/README.md)
first. You need templates 9100-9102 built and the Ansible Vault populated.

All commands run from the `infra/` directory and prompt for your vault
password.

## Provision VM and deploy application

Create the VM and deploy the app in one command:

```bash
cd infra
make up
```

This runs:
1. `provision-vm` — Terraform clones template 9102, creating VM
   `yyz-app-dsv01` at `10.0.20.80`
2. `deploy-app` — Ansible SSHs into the VM, clones the repo, templates the
   `.env` file, and runs `docker compose up -d --build`

The app will be available at `http://10.0.20.80:5000` once deployment completes.

## Appendix

## Deploy App Only (VM Already Exists)

If the VM is already running and you just want to deploy or update the app:

```bash
make deploy-app
```

This is idempotent:
- If the repo doesn't exist on the VM, it clones it
- If the repo exists, it pulls the latest code
- It always re-templates the `.env` file from the vault
- It always runs `docker compose up -d --build`

## Redeploy App

### Full wipe (containers + volumes + repo)

```bash
make redeploy-app
```

This removes all containers, Docker volumes (including database data), and the
cloned repo, then deploys fresh. The database will be re-seeded from the CSV
on startup.

### Keep data (containers + repo only, volumes preserved)

```bash
make redeploy-app-keep-data
```

This stops containers and removes the repo, but preserves Docker volumes. On
redeploy, the database retains its data — no re-seeding needed.

## Destroy App Only

### Full wipe

```bash
make destroy-app
```

Runs `docker compose down -v` (removes containers and volumes) and deletes the
cloned repo from the VM. The VM itself stays running.

### Keep data

```bash
make destroy-app-keep-data
```

Runs `docker compose down` (removes containers, keeps volumes) and deletes the
repo. The VM stays running and volumes persist.

## Destroy Everything

Tear down the app and delete the VM entirely:

```bash
make down
```

This runs `destroy-app` then `destroy-vm` (Terraform destroy). The VM is
removed from Proxmox. To start fresh, run `make up`.

## Destroy VM Only

If you just want to delete the VM without cleaning up Docker first:

```bash
make destroy-vm
```

This runs `terraform destroy` which deletes the VM from Proxmox.

## Rebuild Images

When to rebuild each layer:

| Layer | When to rebuild |
|-------|----------------|
| ubuntu-base (9100) | Monthly, after Ubuntu security advisories, or to update common packages |
| ubuntu-docker (9101) | Docker major version releases, or when base is rebuilt |
| dsv-app (9102) | When docker layer is rebuilt, or when GitHub App key is rotated |

To rebuild a single layer:

```bash
make bake-base       # Layer 1 only
make bake-docker     # Layer 2 only
make bake-dsv-app    # Layer 3 only
```

To rebuild all layers:

```bash
make bake-all
```

After rebuilding, you must destroy and reprovision the VM to use the new
template:

```bash
make down && make up
```

## Troubleshooting

### SSH connection timeout during deploy

The VM may not be fully booted yet. Wait 30 seconds and retry:
```bash
make deploy-app
```

If it persists, verify the VM is running in the Proxmox UI and that
`10.0.20.80` is reachable:
```bash
ping 10.0.20.80
ssh adm-ubuntu@10.0.20.80
```

### Vault password error

Ansible Vault prompts for a password on every command. If you get a decryption
error, verify you're using the correct password:
```bash
cd infra/ansible && ansible-vault view vault/secrets.yml --ask-vault-pass
```

### Docker Compose fails to start

SSH into the VM and check manually:
```bash
ssh adm-ubuntu@10.0.20.80
cd ~/app/DineSafeViz
docker compose logs
```

### Terraform state mismatch

If the VM was deleted manually outside of Terraform:
```bash
cd infra/terraform
# Render tfvars first
cd .. && ansible-vault view ansible/vault/secrets.yml --ask-vault-pass \
  | python3 scripts/render-tfvars.py > terraform/terraform.tfvars
cd terraform && terraform refresh
```

Then reprovision: `cd .. && make provision-vm`
Clean up: `rm terraform/terraform.tfvars`

### Packer build fails

Check the Packer output for the specific error. Common issues:
- Template with the target ID already exists — delete it in Proxmox first
- Proxmox API token expired — regenerate in Proxmox and update the vault
- SSH timeout — ensure the source template has cloud-init configured with
  your SSH key