# Journal 69 — Packer SSH hang: guest agent IP handoff

## 2026-05-18 — Investigate Packer "Waiting for SSH" hang

**Summary:** `make bake-base` hangs at "Waiting for SSH to become
available." VM boots, cloud-init runs, SSH host keys generated, but
`cloud-final.service` fails. Packer never connects.

**Prior context (journal-68):** Guest agent was missing from the cloud
image; fixed by adding `virt-customize --install qemu-guest-agent`.
Template 9000 was rebuilt from scratch with all fixes from journal-68.

**Current state:**
- `virt-customize --install qemu-guest-agent` ran successfully
- Template 9000 created with `--agent enabled=1`, `--ipconfig0 ip=dhcp`,
  `--scsihw virtio-scsi-pci`, `--ciuser ubuntu`
- SSH key set via `qm set 9000 --sshkeys /tmp/iac.pub`
- Packer config has `qemu_agent = true`, `ipconfig { ip = "dhcp" }`,
  `ssh_username = "ubuntu"`, `ssh_timeout = "15m"`
- Packer creates ephemeral key pair, clones VM, starts it, then hangs

**Screenshot observations:**
- SSH host key fingerprints generated (cloud-init config stage succeeded)
- `[FAILED] Failed to start cloud-init_final.service`
- `Reached target cloud-init.target`
- DataSource: NoCloud from /dev/sr0 (Proxmox cloud-init ISO)
- Boot completed in ~22.63 seconds

**Research (context7 — packer-plugin-proxmox):**
- `qemu_agent = true` tells Packer to poll Proxmox API
  (`GET /nodes/{node}/qemu/{vmid}/agent/network-get-interfaces`) for IP
- If agent not responding → Proxmox returns 500 → Packer retries silently
  until `ssh_timeout` (15 min)
- Reference examples include `cloud_init = true` and
  `cloud_init_storage_pool = "local-lvm"` — our config omits these

**Research (web — virt-customize + guest agent):**
- `qemu-guest-agent` is a **static** systemd service (no `[Install]`
  section). It activates via a **udev rule** when the virtio-serial
  device `/dev/virtio-ports/org.qemu.guest_agent.0` appears. This means
  `virt-customize --install` is sufficient — `systemctl enable` is
  neither needed nor effective.
- `virt-customize` sets `/etc/machine-id` by default. For template
  images this is harmful: systemd-networkd uses machine-id as the DHCP
  client identifier (DUID). A pre-set machine-id means all clones share
  the same DUID, causing duplicate DHCP leases or no IP at all.
- Sources: packer-plugin-proxmox#91, Proxmox forums, Ubuntu bugs

**Diagnosis — two issues:**

1. **machine-id (likely root cause):** `virt-customize` sets a random
   machine-id in the image. When the clone boots, networkd uses this
   machine-id as the DHCP DUID. If a previous failed Packer run left a
   stale DHCP lease with the same DUID, the DHCP server may refuse to
   assign a new lease, or the VM gets no IP at all. Fix: truncate
   `/etc/machine-id` so systemd regenerates it on first boot.

2. **cloud-init final stage failure (secondary):** Needs investigation
   but likely unrelated to IP handoff — SSH host keys were generated,
   meaning the config stage succeeded.

**Recommended fix for template 9000 creation:**
```bash
virt-customize -a /var/lib/vz/template/iso/ubuntu-24.04-cloud.img \
  --install qemu-guest-agent \
  --run-command 'truncate -s 0 /etc/machine-id'
```

**Diagnostic commands to run on Proxmox host (while Packer is waiting):**
```bash
qm agent 9100 ping                        # does agent respond?
qm agent 9100 network-get-interfaces      # what IP does it report?
qm guest cmd 9100 get-osinfo              # is guest OS up?
```

## 2026-05-18 — Apply machine-id fix to docs and code

User aborted the build and deleted template 9000.

**Files updated:**
- `docs/how-to/install-guide-iac.md` — added `--run-command 'truncate
  -s 0 /etc/machine-id'` to virt-customize command and explanatory
  paragraph about why machine-id must be truncated (DHCP DUID collision)
- `docs/superpowers/plans/2026-05-10-iac.md` — rewrote Step 2 to match
  current install guide (was stale: missing virt-customize, wrong boot
  syntax `--boot c --bootdisk scsi0`, missing `--ipconfig0 ip=dhcp`,
  missing `--scsihw virtio-scsi-pci` in `qm create`)

**No change needed:**
- `infra/ansible/roles/base/tasks/main.yml:177` — already truncates
  machine-id during Layer 1 provisioning (defense in depth)
- `docs/superpowers/specs/2026-05-10-iac-design.md` — design doc, not
  procedure; seed image section just references the install guide

## 2026-05-18 — Machine-id fix worked but sshd still down

Rebuilt template 9000 with machine-id truncation. Ran `make bake-base`.
Packer still hangs at "Waiting for SSH."

**Diagnostic results (from Proxmox host, VM 9100 running):**
```
qm agent 9100 ping                          # OK — agent responds
qm agent 9100 network-get-interfaces        # eth0 = 10.0.20.246/24
ssh -v ubuntu@10.0.20.246                    # Connection refused
systemctl is-active ssh.service              # inactive
systemctl is-active ssh.socket               # inactive (but enabled)
systemctl is-enabled ssh.service             # disabled
systemctl is-enabled ssh.socket              # enabled
dpkg -l openssh-server                       # iU (unpacked, not configured!)
```

**Root cause:** `openssh-server` is in dpkg `iU` state — unpacked but
not configured. `virt-customize --install qemu-guest-agent` runs inside
a libguestfs appliance with no running systemd. `apt-get update` sees a
newer `openssh-server` security patch (v9.6p1-3ubuntu13.16), unpacks it,
but the postinst fails silently on `systemctl restart ssh` calls. The
package is left half-configured → `ssh.socket` never activates → port
22 refuses connections → Packer hangs.

**Initial fix attempt (dpkg --configure -a):** Did NOT work. The
`dpkg --configure` also calls the postinst, which hits `invoke-rc.d`
→ `systemctl`, which fails in the chroot. Package stays `iU`.

## 2026-05-18 — Full kill chain identified + policy-rc.d fix

Rebuilt template with `dpkg --configure -a`. Same result: openssh-server
still `iU`, sshd dead.

**Diagnostics (VM 9100 running):**
```
dpkg -l openssh-server                       # still iU
ssh.socket status                            # was active 20:31:00,
                                             # deactivated at 20:31:08
cloud-init.log                               # cc_package_update_upgrade_install
                                             # ran apt-get dist-upgrade → exit 100
```

**Full kill chain:**
1. VM boots → systemd starts `ssh.socket` (listening on :22)
2. Cloud-init final stage fires `cc_package_update_upgrade_install`
3. Module runs `apt-get dist-upgrade`
4. apt encounters openssh-server in `iU` → tries to configure it
5. openssh-server postinst calls `invoke-rc.d ssh stop`
6. ssh.socket dies (20:31:08)
7. postinst fails → apt fails (exit 100) → cloud-final fails
8. ssh.socket stays dead → port 22 refuses → Packer hangs

**Why `dpkg --configure -a` doesn't fix it in virt-customize:**
Same problem as the original install — the postinst calls
`invoke-rc.d` which calls `systemctl`, which fails without systemd.
The configure step fails and the package stays `iU`.

**Attempted fix — `/usr/sbin/policy-rc.d`:** policy-rc.d returning
exit 101 tells invoke-rc.d to skip service operations. Should let
postinst complete. **Did not work** — openssh-server still `iU`.

## 2026-05-18 — Simplify: apt-mark hold openssh-server

Previous approaches (dpkg --configure -a, policy-rc.d) failed to fix
openssh-server's `iU` state inside virt-customize. Simplest approach:
**prevent the upgrade entirely** with `apt-mark hold`.

The Ansible base role handles real package upgrades later on a running
system. The seed image just needs openssh-server untouched.

**Updated virt-customize command:**
```bash
virt-customize -a image.img \
  --run-command 'apt-get update && apt-mark hold openssh-server' \
  --install qemu-guest-agent \
  --run-command 'apt-mark unhold openssh-server' \
  --run-command 'truncate -s 0 /etc/machine-id'
```

**Files updated:**
- `docs/how-to/install-guide-iac.md` — simplified virt-customize to
  use apt-mark hold instead of policy-rc.d
- `docs/superpowers/plans/2026-05-10-iac.md` — same

## 2026-05-18 — apt-mark hold also failed; abandon virt-customize

`apt-mark hold openssh-server` did not prevent the `iU` state.
virt-customize's `--install` handler likely runs its own apt operations
that ignore or reset the hold. Four approaches tried, all failed:
1. `dpkg --configure -a` — postinst fails (no systemd)
2. `policy-rc.d` — didn't help
3. `apt-mark hold openssh-server` — ignored by `--install`
4. Variations of the above

**New approach: drop virt-customize entirely.**
- Seed template (9000): plain cloud image, no modification
- Layer 1 Packer config: static IP (`ssh_host`) instead of
  DHCP + guest agent. Packer knows the IP, doesn't need the agent.
- Ansible base role: installs `qemu-guest-agent` on a running system
  (no chroot issues)
- Layers 2+: clone from templates that already have the agent;
  `qemu_agent = true` + DHCP works as before

**Files changed:**
- `infra/packer/ubuntu-base.pkr.hcl` — removed `qemu_agent = true`,
  added `ssh_host = var.build_ip`, changed ipconfig from DHCP to
  static (`${var.build_ip}/24`), added `nameserver`, added
  `build_ip` and `network_gateway` variables (defaults: 10.0.20.200,
  10.0.20.1)
- `infra/ansible/roles/base/tasks/main.yml` — added
  `qemu-guest-agent` to common packages list
- `docs/how-to/install-guide-iac.md` — removed entire virt-customize
  section, simplified to plain cloud image import
- `docs/superpowers/plans/2026-05-10-iac.md` — same

**Design note:** Only Layer 1 needs the static IP workaround. Layers
2 and 3 are unchanged — they clone from templates with the agent and
use `qemu_agent = true` + DHCP.
