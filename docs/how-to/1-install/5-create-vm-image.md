# Create VM Image

Build all three layers in order. Each command will prompt for your vault
password.

```bash
cd infra

# Layer 1: ubuntu-base (template 9100)
make bake-base

# Layer 2: ubuntu-docker (template 9101)
make bake-docker

# Layer 3: dsv-app (template 9102)
make bake-dsv-app
```

Or build all at once:
```bash
make bake-all
```

Each build takes approximately 5-15 minutes depending on network speed and
Proxmox host performance.

## Verify

Check that all three templates exist in the Proxmox UI:

| Template ID | Name | Description |
|-------------|------|-------------|
| 9000 | ubuntu-2404-cloud | Upstream cloud image (seed) |
| 9100 | ubuntu-base | Hardened Ubuntu (Layer 1) |
| 9101 | ubuntu-docker | Ubuntu + Docker CE (Layer 2) |
| 9102 | dsv-app | App VM identity + GitHub key (Layer 3) |

You can also verify from the command line:
```bash
ssh root@10.0.20.21 "qm list" | grep -E "9[01][0-9]{2}"
```

## Next Steps

The image pipeline is complete. To provision a VM and deploy the app, see the
[IaC Deploy Guide](deploy-guide-iac.md).