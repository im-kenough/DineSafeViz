# Load the Cloudflare tunnel token into Key Vault

`cloudflared` on the VM connects to Cloudflare with the tunnel token.
`scripts/fetch-secrets.sh` reads it from `dsv-tunnel-token` in the vault at
deploy time, so it has to be in the vault before the first deploy.

## Prerequisites

- The tunnel `tun-dsv-<env>01` exists, and its token is saved in Bitwarden.
  To create it, see
  [azure-checklist step 5.1](../../../docs/how-to/azure-vm/azure-checklist.md#51-create-the-tunnel-and-store-its-token).
- Signed in as `dsv-ops01` (`az login`). The operators group manages the
  vault's secrets.
- On your home network. The vault firewall only allows your home IP and
  the VM subnet.

## 1. Store the token

Paste the token from Bitwarden when prompted. `read -s` keeps it off the
screen and out of shell history:

```bash
ENV=prod    # or stg
read -rsp "Tunnel token: " TUNNEL_TOKEN; echo
az keyvault secret set --vault-name "kv-dsv-${ENV}01" -n dsv-tunnel-token \
  --value "$TUNNEL_TOKEN" -o none
unset TUNNEL_TOKEN
```

- Rerunning it replaces the value with a new version.
- `ForbiddenByRbac` means a new role assignment hasn't applied yet. Wait a
  few minutes and retry.

## 2. Verify

Without printing the token:

```bash
az keyvault secret show --vault-name "kv-dsv-${ENV}01" -n dsv-tunnel-token \
  --query "{updated:attributes.updated, length:length(value)}" -o table
```

- `updated` is now, and `length` matches the token (usually 180+ characters).
- The next `./scripts/deploy.sh` picks it up. Its tunnel check passes once
  `cloudflared` connects.

## Next

- Route the hostname to nginx, see
  [azure-checklist step 5.2](../../../docs/how-to/azure-vm/azure-checklist.md#52-route-the-hostname-to-nginx).
- Deploy, see [Deploy to prod](../deploy/deploy-prod.md).
