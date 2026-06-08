# Journal 68 — Proxmox Packer Permission Fix

## 2026-05-18 — Diagnose `VM.Config.HWType` permission error

**Summary:** `make bake-base` fails with `403 Permission check failed
(/vms/9100, VM.Config.HWType)`.

**Error (verbatim):**
```
error updating VM: 403 Permission check failed (/vms/9100, VM.Config.HWType)
```
Params sent by Packer include `agent:1`, `cpu:kvm64`,
`net0:e1000=...,bridge=vmbr0` — all of which require the
`VM.Config.HWType` privilege in Proxmox VE 8.x.

**Root cause:** The `Packer` custom role defined in
`docs/how-to/install-guide-iac.md:82` is missing the
`VM.Config.HWType` privilege. Proxmox VE 8.x split hardware-type
settings (CPU type, NIC model, QEMU agent flag) into a dedicated
privilege that didn't exist in earlier versions.

**Current role privs (from install guide):**
```
VM.Allocate VM.Clone VM.Config.Disk VM.Config.CPU VM.Config.Memory
VM.Config.Network VM.Config.Options VM.Config.Cloudinit VM.Audit
VM.Console VM.PowerMgmt Datastore.AllocateSpace Datastore.Audit
Sys.Modify SDN.Use
```

**Fix:** Add `VM.Config.HWType` to the role. On the Proxmox host:
```bash
pveum role modify Packer -privs "VM.Allocate VM.Clone VM.Config.Disk VM.Config.CPU VM.Config.Memory VM.Config.Network VM.Config.Options VM.Config.Cloudinit VM.Config.HWType VM.Audit VM.Console VM.PowerMgmt Datastore.AllocateSpace Datastore.Audit Sys.Modify SDN.Use"
```

**Docs updated:**
- `docs/how-to/install-guide-iac.md:82` — added `VM.Config.HWType` to
  Packer role
- `docs/how-to/install-guide-iac.md:102` — added `VM.Config.HWType` to
  Terraform role (also uses `agent { enabled = true }`)
- `docs/superpowers/plans/2026-05-10-iac.md:2279` — added
  `VM.Config.HWType` to PVE_Packer role
- `docs/superpowers/plans/2026-05-10-iac.md:2298` — added
  `VM.Config.HWType` to PVE_Terraform role
- `docs/ref/arch/arch-security.md` — already uses `VM.Config.*`
  wildcard, no change needed
- `docs/superpowers/specs/2026-05-10-iac-design.md` — already uses
  `VM.Config.*` wildcard, no change needed

## 2026-05-18 — Fix `LABEL=cloudimg-rootfs` boot failure

**Summary:** After fixing permissions, the cloned VM drops to initramfs
with `ALERT! LABEL=cloudimg-rootfs does not exist!`

**Root cause:** The Packer `proxmox-clone` builder defaults
`scsi_controller` to `lsi`. The Ubuntu cloud image seed (template 9000)
uses `virtio-scsi-pci`. The mismatched controller means the kernel's
initramfs can't see the disk, so the root label is never found.

Additionally, the NIC model defaults to `e1000` instead of `virtio`.

**Fix:** Added `scsi_controller = "virtio-scsi-pci"` and
`model = "virtio"` to all three Packer templates:
- `infra/packer/ubuntu-base.pkr.hcl`
- `infra/packer/ubuntu-docker.pkr.hcl`
- `infra/packer/dsv-app.pkr.hcl`

## 2026-05-18 — Fix networkd timeout + adjust resources

**Summary:** Cloned VM waits 3+ minutes for networkd. Cloud-init has no
network config from Packer, so it doesn't configure DHCP and networkd
stalls.

**Fix:** Added `ipconfig { ip = "dhcp" }` to all three Packer templates.
This tells cloud-init to configure DHCP on the first NIC during boot.

**Resource changes per user request:**
- Layers 1, 2 (ubuntu-base, ubuntu-docker): 4 vCPU, 6 GB RAM
  (more headroom during Ansible provisioning)
- Layer 3 (dsv-app): 2 vCPU, 2 GB RAM (unchanged — right-sized
  for the final app template)

**Also added:** `qemu_agent = true` to all three templates. This tells
Packer to use the QEMU guest agent to discover the VM's DHCP IP address.
Without it, Packer generates and injects the SSH key via cloud-init but
has no IP to connect to. This is distinct from the Proxmox hardware
`agent:1` flag — that enables the device, this tells Packer to query it.

## 2026-05-18 — Root cause: qemu-guest-agent not in cloud image

**Summary:** After all previous fixes, Packer still hangs on
"Waiting for SSH to become available." VM boots, shows SSH keys,
cloud-final.service fails, login prompt appears.

**Root cause confirmed:** Ubuntu 24.04 cloud images do NOT include
`qemu-guest-agent`. Verified by checking the official manifest at
`cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.manifest`.
Zero QEMU packages — only `open-vm-tools` (VMware) is included.

With `qemu_agent = true`, Packer polls Proxmox API for the VM's IP
via the guest agent. No agent running → Proxmox returns 500 → Packer
retries silently until `ssh_timeout` (15m). Known issue:
hashicorp/packer-plugin-proxmox#91.

**Fix:** Use `virt-customize` (from `libguestfs-tools`) to inject
`qemu-guest-agent` into the cloud image before importing into Proxmox.
This is preferred over boot-and-install because booting assigns a
`machine-id` that persists across clones.

**Additional template 9000 fixes:**
- `--boot c --bootdisk scsi0` → `--boot order=scsi0` (PVE 8.x syntax)
- Added `--ipconfig0 ip=dhcp` default
- Added `--scsihw virtio-scsi-pci` to `qm create` (Proxmox docs
  requirement for Ubuntu cloud images)
- Memory/cores on seed template reduced to 2048/2 (Packer overrides
  these on clones anyway)

**Updated:** `docs/how-to/install-guide-iac.md` — full rewrite of
the template 9000 setup section.

**Networking design:**
- Layers 1, 2: DHCP — ephemeral build VMs, no static IP needed
- Layer 3: static IP baked in by Ansible dsv-app role via netplan
- No MAC address pinning needed at any layer
