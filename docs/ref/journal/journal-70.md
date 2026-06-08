# Journal 70 — Ansible role not found in Packer build

## 2026-05-18 — Fix ANSIBLE_ROLES_PATH for Packer provisioner

**Summary:** `make bake-base` failed with "role 'base' was not found."

**Error:**
```
ERROR! the role 'base' was not found in
/home/sam/SCM/github/DineSafeViz/infra/ansible/playbooks/roles:
/home/sam/.ansible/roles:...
```

**Root cause:** `ansible.cfg` sets `roles_path = roles` (relative path).
Ansible resolves relative paths relative to CWD at invocation time, not
relative to the config file's location. Packer runs from `infra/packer/`
(Makefile: `cd packer && packer build ...`), so `roles_path = roles` resolves
to `infra/packer/roles/` — nonexistent. Ansible's fallback is a `roles/`
directory adjacent to the playbook file (`infra/ansible/playbooks/roles/`),
also nonexistent. The actual roles are at `infra/ansible/roles/`.

Additionally, ansible-playbook invoked by Packer's provisioner doesn't
automatically pick up `infra/ansible/ansible.cfg` (it's not in CWD or on the
ANSIBLE_CONFIG env var path), so the `roles_path` setting there never applies.

**Fix:** Add `ANSIBLE_ROLES_PATH=../ansible/roles` to `ansible_env_vars` in
all three Packer configs. This resolves to `infra/ansible/roles/` from
Packer's CWD (`infra/packer/`), bypassing the ansible.cfg lookup entirely.

**Files changed:**
- `infra/packer/ubuntu-base.pkr.hcl` — added `ANSIBLE_ROLES_PATH`
- `infra/packer/ubuntu-docker.pkr.hcl` — same
- `infra/packer/dsv-app.pkr.hcl` — same

## 2026-05-18 — Fix Ansible file transfer failure (AnsiballZ_setup.py)

**Error:**
```
fatal: [default]: FAILED! => {"msg": "failed to transfer file to
/home/sam/.ansible/tmp/ansible-local-.../tmp... 
/home/ubuntu/.ansible/tmp/.../AnsiballZ_setup.py:\n\n"}
```

**Root cause:** Packer's ansible provisioner uses a local SSH proxy by
default. This proxy only handles exec channels — not SFTP subsystem.
Ansible's `Gathering Facts` step transfers `AnsiballZ_setup.py` to the
remote host via SFTP, which fails silently through the proxy (empty error).

**Fix:** Add `use_proxy = false` to the ansible provisioner block. Packer
then passes the actual VM IP (10.0.20.200) and ephemeral key directly to
ansible-playbook, bypassing the proxy. Works here because the Packer host
has direct network access to the VM on the same LAN.

Note: `ubuntu-docker.pkr.hcl` and `dsv-app.pkr.hcl` will need the same
fix — they also use DHCP+guest-agent (so known IPs) or static IPs and
will hit the same proxy limitation.

**File changed:**
- `infra/packer/ubuntu-base.pkr.hcl` — added `use_proxy = false`

## 2026-05-18 — Fix `service_account` undefined (group_vars not found)

**Error:**
```
'service_account' is undefined
```

**Root cause:** Ansible loads `group_vars/` from two places: adjacent to the
inventory file, and adjacent to the playbook file. Packer creates a temp
inventory in `/tmp/` — no `group_vars/` there. The playbooks are in
`infra/ansible/playbooks/` and `group_vars/` is one level up at
`infra/ansible/group_vars/` — not visible to Ansible.

**Fix:** Created symlink `infra/ansible/playbooks/group_vars -> ../group_vars`.
Ansible now finds `group_vars/all.yml` via the playbook directory search path.
Git tracks this as a regular symlink entry (stores the target string).

No vault variables are needed by the base role — `service_account`,
`vm_timezone`, and `network_dns` are all plain values in `group_vars/all.yml`.

**File created:**
- `infra/ansible/playbooks/group_vars` — symlink to `../group_vars`

## 2026-05-18 — Fix dpkg lock (cloud-init race condition)

**Error:**
```
E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 2042 (apt-get)
```

**Root cause:** Ubuntu cloud-init runs `apt-get` on first boot (package
upgrade/install stage). Ansible reaches the `apt dist-upgrade` task before
cloud-init finishes, hitting the dpkg lock.

**Fix:** Added a `cloud-init status --wait` task to the base role before any
apt operations. This blocks until cloud-init completes cleanly.

**File changed:**
- `infra/ansible/roles/base/tasks/main.yml` — added wait-for-cloud-init task
  before `Update apt cache and upgrade all packages`

## 2026-05-18 — cloud-init status: error; use failed_when: false

`cloud-init status --wait` returns rc=1 with `status: error`. Cloud-init
exits non-zero on the final stage (same cloud-final package upgrade failure
described in earlier sessions), but the system IS running, SSH IS connected,
and the dpkg lock IS released.

Added `failed_when: false` to the wait task. We need cloud-init to be done
(so the dpkg lock is free), not to have succeeded.

**File changed:**
- `infra/ansible/roles/base/tasks/main.yml` — added `failed_when: false`

## 2026-05-18 — apt fails: No space left on device (seed image disk too small)

**Error:**
```
cannot copy extracted data for './usr/lib/snapd/snap-recovery-chooser'
to '/usr/lib/snapd/snap-recovery-chooser.dpkg-new':
failed to write (No space left on device)
```

**Root cause:** Ubuntu 24.04 cloud image ships with a 2GB virtual disk.
The upgrade has 1 package to install (snapd, 35.2MB) but also needs to
configure `83 not fully installed or removed` packages left by cloud-init's
earlier failure. Together they exhaust the 2GB disk.

**Fix — Proxmox host:** `qm resize 9000 scsi0 60G`

**Fix — IAC code:** All images standardized to 60G, thin provisioned.

Files changed:
- `infra/packer/ubuntu-base.pkr.hcl` — added `disks` block (60G, discard=true)
- `infra/packer/ubuntu-docker.pkr.hcl` — same
- `infra/packer/dsv-app.pkr.hcl` — same
- `infra/terraform/variables.tf` — `vm_disk_size` default 20 → 60
- `infra/ansible/group_vars/all.yml` — `vm_disk_size` 20 → 60
- `docs/how-to/install-guide-iac.md` — added `qm resize 9000 scsi0 60G`

## 2026-05-18 — sshd validate fails: Missing privilege separation directory

**Error:** `Missing privilege separation directory: /run/sshd`

**Root cause:** The `template` task uses `validate: "sshd -t -f %s"` to check
the config before deploying. `sshd -t` requires `/run/sshd` to exist. On this
fresh cloud image, sshd runs via socket activation — the sshd daemon itself
never started, so `/run/sshd` was never created by systemd.

**Fix:** Added a task to create `/run/sshd` before the template deployment.
`/run` is tmpfs so this doesn't persist to the template — it only needs to
exist during the Packer build for the validate step to pass. When a real VM
boots from the template, systemd creates `/run/sshd` when sshd.service starts.

**File changed:**
- `infra/ansible/roles/base/tasks/main.yml` — create `/run/sshd` before
  deploying sshd_config

## 2026-05-18 — Handler fails: sshd service not found

**Error:** `Could not find the requested service sshd: host`

**Root cause:** Handler uses `name: sshd`. On Ubuntu 24.04 the SSH service
is named `ssh`, not `sshd` (Debian convention, unlike RHEL-based distros).

**Fix:** `infra/ansible/roles/base/handlers/main.yml` — `sshd` → `ssh`

## 2026-05-18 — Ansible green; Proxmox 403 on template conversion

All 30 Ansible tasks passed (`ok=30, failed=0`). Packer fails converting the
VM to template:

```
403 Permission check failed (/vms/9100, VM.Config.CDROM)
```

Packer's service account is missing `VM.Config.CDROM`. Packer needs it to
detach the cloud-init drive when finalizing the template.

**Fix on Proxmox host:**
```bash
pveum role modify Packer -privs "VM.Allocate VM.Clone VM.Config.CDROM \
  VM.Config.Disk VM.Config.CPU VM.Config.Memory VM.Config.Network \
  VM.Config.Options VM.Config.Cloudinit VM.Config.HWType VM.Audit \
  VM.Console VM.PowerMgmt Datastore.AllocateSpace Datastore.Audit \
  Sys.Modify SDN.Use"
```

**File updated:**
- `docs/how-to/install-guide-iac.md` — added `VM.Config.CDROM` to Packer role
