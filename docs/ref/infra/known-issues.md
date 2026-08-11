# Known issues: infrastructure build toolchain

Documented behavioral quirks in the IaC build toolchain (Packer, Ansible,
Proxmox) that are not bugs to fix but constraints to work around. Each entry
explains the symptom, root cause, and the applied mitigation.

---

## Packer ansible provisioner: SFTP file transfer fails silently

**Affects:** All Packer templates (`ubuntu-base`, `ubuntu-docker`, `dsv-app`)

**Symptom:**

Packer connects to the VM (SSH is up, guest agent responds) but Ansible fails
immediately during `Gathering Facts` with an empty file transfer error:

```
fatal: [default]: FAILED! => {"msg": "failed to transfer file to
/home/ubuntu/.ansible/tmp/.../AnsiballZ_setup.py:\n\n"}
```

**Root cause:**

Packer's ansible provisioner defaults to routing all SSH traffic through a
local proxy it manages. This proxy only handles exec channels — it does not
implement the SFTP subsystem. Ansible's `Gathering Facts` step must upload
`AnsiballZ_setup.py` to the remote host via SFTP before it can run any tasks.
That upload fails silently through the proxy, producing a blank error message.

**Mitigation:**

All three Packer templates set `use_proxy = false` on the ansible provisioner.
This causes Packer to pass the real VM IP address and an ephemeral SSH key
directly to `ansible-playbook`, which then manages its own SSH connection
(including SFTP). This works because the Packer host has direct LAN access to
the build VMs on `10.0.20.0/24`.

**Constraint:** `use_proxy = false` requires the Packer host to have direct
network reachability to the build VM. If the build environment changes (for
example, Packer running in a CI runner with no direct VM access), the proxy
limitation would need a different workaround (for example, an `sftp_command`
override or a bastion).
