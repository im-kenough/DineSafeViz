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

Perform initial app setup

run updates
install docker, jq

## Configure application

cp deploy/stg.env-example deploy/stg.env
