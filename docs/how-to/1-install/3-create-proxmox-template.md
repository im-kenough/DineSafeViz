### Create the proxmox template

Download the Ubuntu cloud image and import it as-is. The cloud image
does not ship with `qemu-guest-agent`, but the Ansible base role
installs it during the Layer 1 build on a running system. The Layer 1
Packer config uses a temporary static IP (`ssh_host`) instead of agent
IP discovery, so the seed template needs no modification.

ssh into the proxmox VM.
```bash
# Download cloud image
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img \
  -O /var/lib/vz/template/iso/ubuntu-24.04-cloud.img

# Create VM with virtio-scsi controller (required for Ubuntu cloud images)
qm create 9000 --name ubuntu-2404-cloud --memory 4096 --cores 4 \
  --net0 virtio,bridge=vmbr0 --scsihw virtio-scsi-pci

# Import disk
qm importdisk 9000 /var/lib/vz/template/iso/ubuntu-24.04-cloud.img local-lvm

# Attach disk and set boot order
qm set 9000 --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --boot order=scsi0

# Resize disk to 60G (cloud image ships with 2G — all VMs use 60G)
qm resize 9000 scsi0 60G

# Add cloud-init drive and serial console
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --serial0 socket --vga serial0

# Enable QEMU guest agent (used after base role installs it)
qm set 9000 --agent enabled=1

# Set cloud-init defaults
qm set 9000 --ciuser adm-ubuntu
qm set 9000 --ipconfig0 ip=dhcp
```

On your workstation, upload your IAC public key into Proxmox's temp dir.
Then tell the VM to import the key from that dir.
Once converted to a template, the image is frozen and persists the
authorized public key.

```bash
cat ~/.ssh/iac.pub | ssh root@10.0.20.21 \
  "cat > /tmp/iac.pub && qm set 9000 --sshkeys /tmp/iac.pub"
```

On the Proxmox server, convert to template.

```bash
qm template 9000
```