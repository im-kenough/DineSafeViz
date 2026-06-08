# Journal 75

## 2026-05-19 — Fix: Resolve Packer SSH hang and enhance image cleanup consistency

**Summary:** Resolved persistent SSH connection hangs during Packer builds by implementing a static IP strategy and enhancing the cleanup process to ensure Cloud-Init and SSH services are properly prepared for cloning.

**Diagnosis:**
1. **SSH Hang:** `ubuntu-docker.pkr.hcl` was relying on DHCP and the QEMU guest agent to report an IP. Delays in agent startup or network assignment caused Packer to wait indefinitely.
2. **SSH Service Failure:** Removing SSH host keys in the `cleanup` role before flushing handlers caused `sshd` to fail during restart.
3. **Apt Lock Contention:** Subsequent build layers hit `dpkg` lock errors because background `apt` processes (unattended-upgrades/cloud-init) were running on first boot.
4. **HCL Parsing Error:** Multi-line secrets (like RSA keys) were being rendered with literal newlines, which is invalid in HCL quoted strings.

**Resolution:**
- **Static IPs:** Implemented dedicated static build IPs for all Packer layers (`10.0.20.200`, `201`, `202`) and updated `render-vars.py` and Packer templates to use them.
- **Robust Cleanup:** 
    - Added `meta: flush_handlers` to all roles (`base`, `docker`, `dsv-app`) to ensure service restarts happen before host-key removal.
    - Enhanced the `cleanup` role to remove residual Cloud-Init cache and ensure unique host-key regeneration on the next boot.
- **Settlement Wait:** Added a "System Settlement" task to wait for Cloud-Init and the `dpkg` lock before starting Ansible tasks in `docker` and `dsv-app` roles.
- **HCL Variable Escaping:** Updated `render-vars.py` to escape `\n` characters in values, ensuring multi-line strings are valid HCL.
- **Compatibility:** Updated `sshd_config` to use `KbdInteractiveAuthentication` instead of deprecated `ChallengeResponseAuthentication`.

**Files changed:**
- `infra/ansible/group_vars/all.yml`
- `infra/ansible/roles/base/tasks/main.yml`
- `infra/ansible/roles/base/templates/sshd_config.j2`
- `infra/ansible/roles/cleanup/tasks/main.yml`
- `infra/ansible/roles/docker/tasks/main.yml`
- `infra/ansible/roles/dsv-app/tasks/main.yml`
- `infra/packer/ubuntu-base.pkr.hcl`
- `infra/packer/ubuntu-docker.pkr.hcl`
- `infra/packer/dsv-app.pkr.hcl`
- `infra/scripts/render-vars.py`
