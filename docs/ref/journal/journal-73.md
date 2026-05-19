# Journal 73

## 2026-05-19 — Fix: cloud-init disabled on ubuntu-docker and dsv-app builds

**Summary:** `make bake-docker` hung indefinitely at "Waiting for SSH to become
available." Root cause: cloud-init is disabled on the ubuntu-docker build VM,
so ens18 has no IP and Packer's ephemeral SSH key is never injected.

**Diagnosis:**

```bash
# From Proxmox host — while bake-docker was hung:
qm agent 9101 network-get-interfaces
# Result: only lo (loopback). ens18 listed with no ip-addresses key.

qm guest exec 9101 -- cloud-init status
# Result: "status: disabled"
```

**Root cause:**

Packer removes the cloud-init CDROM drive when it converts a finished build VM
into a Proxmox template (this is why `VM.Config.CDROM` was added to the Packer
role in journal-70 — Proxmox requires that permission for the detach).

Template 9100 (ubuntu-base) therefore has no cloud-init drive attached. When
ubuntu-docker clones from it, the clone (9101) also has no cloud-init drive.
On boot, cloud-init's `ds-identify` finds no NoCloud datasource and writes the
disabled marker. With cloud-init disabled:
- DHCP is never configured → no IP on ens18
- Packer's ephemeral SSH key is never injected into authorized_keys
- Packer can't SSH in → hangs until timeout

The same problem would affect dsv-app (Layer 3), which clones from the
ubuntu-docker template (9101), itself built by Packer.

ubuntu-base (Layer 1) is unaffected: it clones from the seed image (9000),
which has a cloud-init drive attached manually during initial Proxmox setup
and was never stripped by Packer.

**Fix:** Add `cloud_init = true` and `cloud_init_storage_pool = "local-lvm"` to
the source block of ubuntu-docker.pkr.hcl and dsv-app.pkr.hcl. This tells
Packer to create a fresh cloud-init drive on the build VM before booting it,
giving ds-identify a valid NoCloud datasource.

**Files changed:**
- `infra/packer/ubuntu-docker.pkr.hcl` — added `cloud_init` + `cloud_init_storage_pool`
- `infra/packer/dsv-app.pkr.hcl` — same
