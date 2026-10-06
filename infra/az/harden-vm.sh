#!/bin/bash
# Basic OS hardening for vm-dsv-<env>01 (Ubuntu 24.04)
# (azure-checklist.md step 6.3, "harden the OS")
#
# Usage, on the VM as the admin user:
#   scp -i "${SSH_KEY%.pub}" infra/az/harden-vm.sh "$ADMIN_USER@<vm-ip>:/tmp/"
#   sudo bash /tmp/harden-vm.sh
#
# Safe to run again. unattended-upgrades isn't touched: it keeps installing
# security updates daily, alongside Azure Update Manager's maintenance window
# (azure-checklist.md step 6.3). Keep your SSH session open and test a new
# login before you disconnect; the serial console (step 6.4) is the fallback.
set -euo pipefail

ADMIN_USER=${SUDO_USER:?run with sudo from the admin account}
[[ $(id -u) -eq 0 ]] || { echo "ERROR: run with sudo" >&2; exit 1; }
echo "== Hardening for admin user: $ADMIN_USER"

#################################
# 1. SSH: keys only, admin user only
#################################
# 10- sorts before cloud-init's 50-, and sshd keeps the first value it reads.
SSHD_DROPIN=/etc/ssh/sshd_config.d/10-dsv-hardening.conf
cat > "$SSHD_DROPIN" <<CONF
# Managed by infra/az/harden-vm.sh
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
AuthenticationMethods publickey
AllowUsers $ADMIN_USER
MaxAuthTries 3
LoginGraceTime 30
MaxStartups 10:30:60
X11Forwarding no
AllowAgentForwarding no
PermitTunnel no
ClientAliveInterval 300
ClientAliveCountMax 2
CONF
chmod 644 "$SSHD_DROPIN"
if sshd -t; then
    systemctl reload ssh || systemctl restart ssh
    echo "   sshd config valid and reloaded"
else
    echo "ERROR: sshd config invalid; removing $SSHD_DROPIN" >&2
    rm -f "$SSHD_DROPIN"
    exit 1
fi

#################################
# 2. Host firewall (second layer behind the NSG)
#################################
# Docker-published ports bypass ufw; docker-compose.vm.yml publishes none.
apt-get install -y -qq ufw >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH (NSG limits source to home IP)'
ufw --force enable

#################################
# 3. Kernel and network sysctls
#################################
# net.ipv4.ip_forward is left alone; Docker needs it.
cat > /etc/sysctl.d/90-dsv-hardening.conf <<'CONF'
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
fs.suid_dumpable = 0
CONF
sysctl --system >/dev/null

#################################
# 4. No core dumps (they can hold secrets from memory)
#################################
cat > /etc/security/limits.d/90-dsv-nocore.conf <<'CONF'
* hard core 0
CONF
mkdir -p /etc/systemd/coredump.conf.d
cat > /etc/systemd/coredump.conf.d/90-dsv.conf <<'CONF'
[Coredump]
Storage=none
ProcessSizeMax=0
CONF

#################################
# 5. Lock root; persistent, size-capped journal
#################################
passwd -l root >/dev/null
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/90-dsv.conf <<'CONF'
[Journal]
Storage=persistent
SystemMaxUse=200M
MaxRetentionSec=1month
CONF
systemctl restart systemd-journald

#################################
# 6. Verify
#################################
echo; echo "== Effective sshd settings"
sshd -T | grep -Ei '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|authenticationmethods|allowusers|maxauthtries|x11forwarding|allowagentforwarding) '
echo; echo "== Firewall"; ufw status verbose
echo; echo "== Root account"; passwd -S root
echo; echo "== Sample sysctls"
sysctl net.ipv4.conf.all.accept_redirects kernel.kptr_restrict fs.suid_dumpable net.ipv4.ip_forward
echo; echo "Done. Keep this session open and test a NEW ssh login before you disconnect."
