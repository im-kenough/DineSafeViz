# Setup Proxmox

### Create Proxmox service accounts

- SSH into proxmox with root credentials

#### Create `svc-packer`

Create a paker service account `svc-packer` for image builds


```bash
# Create user
pveum user add svc-packer@pve --comment "Packer image build service account"

# Create role with required permissions
pveum role add Packer -privs "VM.Allocate VM.Clone VM.Config.CDROM VM.Config.Disk VM.Config.CPU VM.Config.Memory VM.Config.Network VM.Config.Options VM.Config.Cloudinit VM.Config.HWType VM.Audit VM.Console VM.PowerMgmt Datastore.AllocateSpace Datastore.Audit Sys.Modify SDN.Use"

# Assign role to user on root path
pveum aclmod / -user svc-packer@pve -role Packer

# Create API token (save the output!)
pveum user token add svc-packer@pve packer --privsep 0
```

**Save the token value** — it is only shown once.

#### Create `svc-terraform`

Create a terraform service account `svc-terraform` for vm provisioning

```bash
# Create user
pveum user add svc-terraform@pve --comment "Terraform provisioning service account"

# Create role with required permissions
pveum role add Terraform -privs "VM.Allocate VM.Clone VM.Config.Disk VM.Config.CPU VM.Config.Memory VM.Config.Network VM.Config.Options VM.Config.Cloudinit VM.Config.HWType VM.Audit VM.PowerMgmt VM.GuestAgent.Audit Datastore.AllocateSpace Datastore.Audit SDN.Use"

# Assign role to user on root path
pveum aclmod / -user svc-terraform@pve -role Terraform

# Create API token (save the output!)
pveum user token add svc-terraform@pve terraform --privsep 0
```

Save the token you'll only see it once.