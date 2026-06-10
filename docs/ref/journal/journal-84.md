# Journal Entry - 2026-06-09

## 2026-06-09 10:00 - Fixing Azure CLI Installation on Linux Mint 22.1

### Problem
User unable to install Azure CLI on Linux Mint 22.1 ('xia').
Error: `404 Not Found` for `https://packages.microsoft.com/repos/azure-cli xia Release`.

### Investigation
- `lsb_release -cs` returns `xia`.
- Microsoft's Azure CLI repository does not support `xia`.
- Linux Mint 22.1 is based on Ubuntu 24.04 `noble`.
- Verified `noble` exists in `https://packages.microsoft.com/repos/azure-cli/dists/`.

### Action
- Updated `/etc/apt/sources.list.d/azure-cli.sources` to change `Suites: xia` to `Suites: noble`.
- Running `apt-get update` and `apt-get install azure-cli`.

### Commands
```bash
sudo sed -i 's/Suites: xia/Suites: noble/' /etc/apt/sources.list.d/azure-cli.sources
sudo apt-get update
sudo apt-get install azure-cli
az --version
```

### Result
Azure CLI 2.87.0 successfully installed and verified.
