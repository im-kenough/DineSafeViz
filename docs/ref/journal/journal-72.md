# Journal 72

## 2026-05-19 — Apply `use_proxy = false` to docker and app Packer templates

**Summary:** Journal-70 documented the SSH proxy fix (`use_proxy = false`) and
noted it was only applied to `ubuntu-base.pkr.hcl`. Applied the same fix to
`ubuntu-docker.pkr.hcl` and `dsv-app.pkr.hcl`.

**Root cause (from journal-70):** Packer's ansible provisioner uses a local SSH
proxy by default. This proxy only handles exec channels — not the SFTP
subsystem. Ansible's `Gathering Facts` step uploads `AnsiballZ_setup.py` via
SFTP, which fails silently through the proxy (empty error message). Symptom is
a hang at "Waiting for SSH to become available" followed by an empty file
transfer error.

**Fix:** `use_proxy = false` — Packer passes the real VM IP and ephemeral key
directly to `ansible-playbook`, which opens its own SSH connection (including
SFTP).

**Files changed:**
- `infra/packer/ubuntu-docker.pkr.hcl` — added `use_proxy = false` to ansible provisioner
- `infra/packer/dsv-app.pkr.hcl` — added `use_proxy = false` to ansible provisioner
