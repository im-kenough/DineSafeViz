#!/bin/bash
# Wrapper script to configure and harden a DineSafeViz Azure VM.
# Runs initial setup (docker, swap, IMDS blocking, refresh timer) followed by OS hardening.
#
# Usage (run on the VM as the admin user):
#   bash infra/az/setup-vm.sh
#   # or
#   ./infra/az/setup-vm.sh
#
set -euo pipefail

# Ensure the script is run as a normal user with sudo privileges, not directly as root.
# init-setup-vm.sh needs $USER to configure docker and systemd services,
# while harden-vm.sh requires $SUDO_USER to be set via sudo.
if [[ $(id -u) -eq 0 ]]; then
    echo "ERROR: Do not run setup-vm.sh with sudo or as root." >&2
    echo "Run it as your admin user (e.g., bash infra/az/setup-vm.sh)." >&2
    echo "The script will prompt for or invoke sudo as needed." >&2
    exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

INIT_SCRIPT="$SCRIPT_DIR/init-setup-vm.sh"
HARDEN_SCRIPT="$SCRIPT_DIR/harden-vm.sh"

for script in "$INIT_SCRIPT" "$HARDEN_SCRIPT"; do
    [[ -f $script ]] || { echo "ERROR: script not found: $script" >&2; exit 1; }
done

# Switch to the repo root so relative paths (e.g., deploy/systemd) resolve properly
cd "$REPO_ROOT"

echo "=========================================="
echo "Step 1: Running initial VM setup"
echo "=========================================="
bash "$INIT_SCRIPT"

echo ""
echo "=========================================="
echo "Step 2: Running VM hardening"
echo "=========================================="
sudo bash "$HARDEN_SCRIPT"

echo ""
echo "=========================================="
echo "VM setup and hardening completed."
echo "=========================================="
