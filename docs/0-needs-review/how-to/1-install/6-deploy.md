# Deploy the application

This document shows you how to deploy the DineSafeViz application with the IaC
toolchain.

**Prerequisites:** First, complete the [install guide](README.md). You need
templates 9100 to 9102 built and the Ansible Vault populated.

All commands run from the `infra/` directory and prompt for your Vault
password.

## Provision a VM and deploy the application

To create the VM and deploy the app in one command, run the following.

```bash
cd infra
make up
```

This command runs the following steps:

1. `provision-vm` — Terraform clones template 9102 and creates VM
   `yyz-app-dsv01` at `10.0.20.80`.
2. `deploy-app` — Ansible connects to the VM with SSH, clones the repository,
   templates the `.env` file, and runs `docker compose up -d --build`.

The app is available at `http://10.0.20.80:8080` after the deployment
completes.

## Other operations

The following operations redeploy, destroy, and rebuild the application.

### Deploy the app only (VM already exists)

If the VM already runs and you want to deploy or update the app, run the
following command.

```bash
make deploy-app
```

This command is idempotent:

- If the repository does not exist on the VM, it clones the repository.
- If the repository exists, it pulls the latest code.
- It always re-templates the `.env` file from the Vault.
- It always runs `docker compose up -d --build`.

### Redeploy the app

#### Full wipe (containers, volumes, and repository)

```bash
make redeploy-app
```

This command removes all containers, Docker volumes (including database data),
and the cloned repository. It then deploys fresh. The database re-seeds from
the CSV on startup.

#### Keep the data (containers and repository only, volumes preserved)

```bash
make redeploy-app-keep-data
```

This command stops the containers and removes the repository, but it preserves
the Docker volumes. On redeploy, the database keeps its data, so no re-seeding
is needed.

### Destroy the app only

#### Full wipe

```bash
make destroy-app
```

This command runs `docker compose down -v` to remove the containers and
volumes. It then deletes the cloned repository from the VM. The VM stays
running.

#### Keep the data

```bash
make destroy-app-keep-data
```

This command runs `docker compose down` to remove the containers and keep the
volumes. It then deletes the repository. The VM stays running, and the volumes
persist.

### Destroy everything

To tear down the app and delete the VM, run the following command.

```bash
make down
```

This command runs `destroy-app` and then `destroy-vm` (Terraform destroy).
Terraform removes the VM from Proxmox. To start fresh, run `make up`.

### Destroy the VM only

To delete the VM without cleaning up Docker first, run the following command.

```bash
make destroy-vm
```

This command runs `terraform destroy`, which deletes the VM from Proxmox.

### Rebuild the images

Rebuild each layer in these cases:

| Layer | When to rebuild |
|-------|----------------|
| ubuntu-base (9100) | Monthly, after Ubuntu security advisories, or to update common packages |
| ubuntu-docker (9101) | Docker major version releases, or when base is rebuilt |
| dsv-app (9102) | When docker layer is rebuilt, or when GitHub App key is rotated |

To rebuild a single layer, run one of the following commands.

```bash
make bake-base       # Layer 1 only
make bake-docker     # Layer 2 only
make bake-dsv-app    # Layer 3 only
```

To rebuild all the layers, run the following command.

```bash
make bake-all
```

After you rebuild, destroy and reprovision the VM to use the new template.

```bash
make down && make up
```

## Troubleshooting

### SSH connection timeout during deploy

The VM might not have finished booting. Wait 30 seconds, and then retry.

```bash
make deploy-app
```

If the problem persists, verify that the VM runs in the Proxmox UI and that
`10.0.20.80` is reachable.

```bash
ping 10.0.20.80
ssh adm-ubuntu@10.0.20.80
```

### Vault password error

Ansible Vault prompts for a password on every command. If you get a decryption
error, verify that you use the correct password.

```bash
cd infra/ansible && ansible-vault view vault/secrets.yml --ask-vault-pass
```

### Docker Compose fails to start

Connect to the VM with SSH, and then check the logs.

```bash
ssh adm-ubuntu@10.0.20.80
cd ~/app/DineSafeViz
docker compose logs
```

### Terraform state mismatch

If the VM was deleted manually outside of Terraform, run the following
commands.

```bash
cd infra/terraform
# Render tfvars first
cd .. && ansible-vault view ansible/vault/secrets.yml --ask-vault-pass \
  | python3 scripts/render-vars.py terraform > terraform/terraform.tfvars
cd terraform && terraform refresh
```

Then reprovision the VM.

```bash
cd .. && make provision-vm
```

Then clean up the rendered file.

```bash
rm terraform/terraform.tfvars
```

### Packer build fails

Check the Packer output for the specific error. Common issues include:

- The template with the target ID already exists. Delete it in Proxmox first.
- The Proxmox API token expired. Regenerate it in Proxmox, and then update the
  Vault.
- SSH timeout. Make sure that the source template has cloud-init configured
  with your SSH key.
