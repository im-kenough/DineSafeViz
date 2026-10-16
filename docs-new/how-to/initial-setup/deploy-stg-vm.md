# Deploying stg vm v2

Placeholder until real IAC is introduced

## Configure and deploy VM

On your workstation, configure and run `infra/az/create-gen-vm.sh`

```bash
bash infra/az/create-gen-vm.sh
```
This provisions the VM, storage, public IP and NIC
The VM's ssh admin key and a github deploy key will be uploaded

## Connect to the VM

The script will add the VM to the workstation's SSH config file

```bash
ssh dsv-vm-admin@vm02-dsv-stg01
```
## Clone Repo

```bash
git clone git@github.com:im-kenough/DineSafeViz.git
cd DineSafeViz
```

## Configure VM

### Perform initial setup

Install required apps and perform VM configurations
```bash
bash infra/az/init-setup-vm.sh
```

### Harden VM

Perform basic vm hardening
```bash
bash infra/az/harden-vm.sh
```


## Configure application

Configure the env file
```bash
cp deploy/stg.env-example deploy/stg.env
```

### Initial blob storage ingestion

Only required for brand new environments, otherwise can be skipped.

On a brand-new environment, Blob Storage is empty, so the deploy stops with
`the data load failed and the site has an empty database`. Fill Blob Storage
from Toronto Open Data, then rerun the deploy:

```bash
./scripts/pipeline.sh stg ingest
```

### Deploy application

```bash
./scripts/deploy.sh stg main
docker compose ps
```