# Deploying stg vm v2

Placeholder until real IAC is introduced

## 1. Configure and deploy VM

On your workstation, configure and run `infra/az/create-gen-vm.sh`

```bash
bash infra/az/create-gen-vm.sh
```
This provisions the VM, storage, public IP and NIC
The VM's ssh admin key and a github deploy key will be uploaded
Run it from your clone; it loads shared helpers from `infra/az/vm-lib.sh`

## 2. Connect to the VM

The script will add the VM to the workstation's SSH config file

```bash
ssh dsv-vm-admin@vm02-dsv-stg01
```
## 3. Clone Repo

```bash
git clone git@github.com:im-kenough/DineSafeViz.git
cd DineSafeViz
```

## 4. Configure VM

### 4.1 Perform initial setup

Run the setup wrapper script which runs
- init-setup-vm.sh: installs required apps & performs VM configurations
- harden-vm.sh: performs basic hardening

Run it as the admin user, not with `sudo`; it calls `sudo` as needed.

```bash
bash infra/az/setup-vm.sh
```

When it finishes, open a new SSH session before closing this one. The new
login confirms the hardened SSH settings work and picks up your `docker` group
membership, which the scripts in step 5 need.

## 5. Configure application

Configure the env file
```bash
cp deploy/stg.env-example deploy/stg.env
```

### 5.1 Initial blob storage ingestion

Only required for brand new environments, otherwise can be skipped.

On a brand-new environment, Blob Storage is empty, so the deploy stops with
`the data load failed and the site has an empty database`. Fill Blob Storage
from Toronto Open Data, then rerun the deploy:

```bash
./scripts/pipeline.sh stg ingest
```

### 5.2 Deploy application

```bash
./scripts/deploy.sh stg main
docker compose ps
```

## 6. Reboot and validate

reboot the VM and confirm the stack comes back up and operates normally

```bash
sudo reboot now
```

to do: implement PIV script https://github.com/im-kenough/DineSafeViz/issues/298