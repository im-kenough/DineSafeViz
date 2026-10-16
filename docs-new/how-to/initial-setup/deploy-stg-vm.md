# Deploying stg vm v2

Placeholder until real IAC is introduced

## Configure and deploy VM

On your workstation, configure and run `infra/az/create-gen-vm.sh`

```bash
bash infra/az/create-gen-vm.sh
```
This provisions the VM, storage, public IP and NIC

## Configure workstation ssh config

Edit the ssh config

```bash
nano ~/.ssh/config
```

Insert the VM's host information

```bash
Host vm02-dsv-stg01
  HostName real-ip-goes-here
  User dsv-vm-admin
  IdentityFile ~/.ssh/id_ed25519_dsv_stg01_az_admin
  IdentitiesOnly yes
```

## Configure VM

Clone the repo using the PAT

```bash

```

