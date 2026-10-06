# Set up an Azure VM for its first deploy

This guide prepares a new stg or prod VM to run DineSafeViz. Run it once per VM,
after the Azure resources exist and after you've hardened the OS and installed
Docker. For stg, run it again each time you recreate the VM.

<!-- prettier-ignore -->
> [!NOTE]
> This describes the target state for the Azure VM deployment. Validate each
> step the first time you run it on a real VM, and update this guide with what
> you find.

## Before you begin

Confirm the following before you start. The Azure checklist and your own
hardening steps cover each item.

- The VM is `vm-dsv-stg01` or `vm-dsv-prod01`, running Ubuntu 24.04 LTS.
- The VM's only managed identity is `id-dsv-<env>01-vm`, and that identity has
  Key Vault Secrets User on `kv-dsv-<env>01`.
- The VM's subnet has the `Microsoft.KeyVault` service endpoint, and the vault
  firewall allows that subnet.
- The `kv-dsv-<env>01` vault holds all five secrets listed in the secrets
  inventory.
- The Cloudflare tunnel `tun-dsv-<env>01` exists and routes to
  `http://dsv-nginx:80`.
- Docker Engine and the Docker Compose plugin are installed.
- You can SSH to the VM as your admin user from your home IP address.

In the commands below, replace `stg` with `prod` when you set up prod.

## 1. Install the tools the scripts need

The deploy scripts use `git` and `jq`. Install them, and add your admin user to
the `docker` group so you can run `docker compose` without `sudo`:

```bash
sudo apt-get update && sudo apt-get install -y git jq
sudo usermod -aG docker "$USER"
```

Sign out and back in for the group change to apply.

<!-- prettier-ignore -->
> [!WARNING]
> Membership in the `docker` group is equivalent to root. Your admin user
> already has `sudo`, so this doesn't add privilege, but don't add any other
> account to the group.

## 2. Add a swap file

The prod VM, a B2ats_v2, has 1 GiB of memory, of which `free -h` reports about
836 MiB. A swap file gives the containers headroom so a memory spike slows
the VM down instead of killing Postgres. The stg VM, a B2als_v2, has 4 GiB
and rarely needs swap, but add it anyway so both VMs are set up the same way.

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-dsv-swap.conf
sudo sysctl --system >/dev/null
swapon --show
```

## 3. Block containers from the instance metadata service

Any process that can reach `169.254.169.254` can request a Key Vault token as
the VM's identity. Only the host script `fetch-secrets.sh` needs that, so
block it for containers with a rule in Docker's `DOCKER-USER` chain.

Docker creates the chain each time it starts, so a systemd unit adds the rule
after Docker starts, including after every reboot.

1.  Create the unit file:

    ```bash
    sudo tee /etc/systemd/system/dsv-imds-block.service >/dev/null <<'EOF'
    [Unit]
    Description=Block containers from the Azure instance metadata service
    After=docker.service
    Requires=docker.service
    PartOf=docker.service

    [Service]
    Type=oneshot
    RemainAfterExit=yes
    ExecStart=/bin/sh -c 'iptables -C DOCKER-USER -d 169.254.169.254 -j DROP 2>/dev/null || iptables -I DOCKER-USER -d 169.254.169.254 -j DROP'
    ExecStop=/bin/sh -c 'iptables -D DOCKER-USER -d 169.254.169.254 -j DROP 2>/dev/null || true'

    [Install]
    WantedBy=multi-user.target docker.service
    EOF
    ```

2.  Enable and start it:

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now dsv-imds-block.service
    sudo iptables -S DOCKER-USER
    ```

    The output includes `-A DOCKER-USER -d 169.254.169.254/32 -j DROP`.

3.  Verify that a container can't reach the metadata service. This command
    must time out:

    ```bash
    docker run --rm curlimages/curl -s -m 3 -H Metadata:true \
      "http://169.254.169.254/metadata/instance?api-version=2021-02-01" \
      && echo "NOT BLOCKED" || echo "Blocked"
    ```

4.  Verify that the host still can. This prints a number of seconds, not the
    token:

    ```bash
    curl -s -H Metadata:true \
      "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net" \
      | jq -r '.expires_in'
    ```

There's a short window during boot, between Docker starting the containers and
the unit adding the rule, when the rule isn't in place. The containers that run
at that point are the app's own, so this is an accepted risk.

## 4. Clone the repository

The repository is public, so cloning needs no credentials:

```bash
git clone https://github.com/im-kenough/DineSafeViz.git ~/DineSafeViz
cd ~/DineSafeViz
```

Then create the environment's settings file from its committed example. The
real file, `deploy/stg.env`, is gitignored, so deploys never overwrite it and
it's never committed. The example holds no secrets, so you don't need to edit
it unless a setting differs on this VM.

```bash
cp deploy/stg.env-example deploy/stg.env
```

## 5. Check Key Vault access from the VM

Before the first deploy, confirm that the VM can list the vault's secrets
through its identity. A firewall or role problem shows up here with a clear
error instead of partway through a deploy.

```bash
TOKEN=$(curl -s -H Metadata:true \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net" \
  | jq -r '.access_token')
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://kv-dsv-stg01.vault.azure.net/secrets?api-version=7.4" \
  | jq -r '.value[].id | split("/") | last'
unset TOKEN
```

The output lists the five secret names. The following table shows what the
common errors mean.

| Error                                  | Cause                                                     |
| -------------------------------------- | --------------------------------------------------------- |
| `ForbiddenByFirewall`                  | The subnet's service endpoint or vault network rule is missing |
| `ForbiddenByRbac`                      | `id-dsv-stg01-vm` has no role on the vault, or the role was assigned in the last few minutes |
| Token request returns `identity not found` | The identity isn't attached to the VM                  |

## 6. Run the first deploy

Deploy the current `main` to stg, or the release tag to prod:

```bash
./scripts/deploy.sh stg main        # prod: ./scripts/deploy.sh prod v0.5.0
docker compose ps
```

All services show `running` or `healthy`, and `dsv-init-db` and
`dsv-init-analytics` show `exited (0)`. The first deploy takes several minutes
because `dsv-init-db` downloads and loads the inspection data.

Then check the tunnel and the site:

1.  In the Cloudflare dashboard, go to **Networking** > **Tunnels**. Confirm
    that `tun-dsv-stg01` shows **Healthy**.
2.  Open `https://stg.dinesafeviz.com` and `https://stg.dinesafeviz.com/analytics/`.

## 7. Confirm the setup survives a reboot

Reboot once to check that the swap file, the metadata block, and the containers
all come back on their own:

```bash
sudo reboot
# after reconnecting:
swapon --show
sudo iptables -S DOCKER-USER | grep 169.254.169.254
cd ~/DineSafeViz && docker compose ps
```

## Sign in to Grafana as admin

The public site returns `404` for the Grafana sign-in page, so admins sign in
through an SSH tunnel instead. Grafana has a fixed address, `172.30.10.30`, on
the VM's internal Docker network, which the VM itself can reach.

1.  On your workstation, get the admin password from the vault. Your home IP
    address must be allowed by the vault firewall.

    ```bash
    az keyvault secret show --vault-name kv-dsv-stg01 \
      -n dsv-analytics-admin-password --query value -o tsv
    ```

2.  Open the tunnel and leave it running:

    ```bash
    ssh -N -L 3000:172.30.10.30:3000 <admin-user>@<vm-public-ip>
    ```

3.  Open `http://localhost:3000/analytics/login` and sign in as
    `dsv-analytics-admin`, the `DSV_ANALYTICS_ADMIN_USER` in
    `deploy/stg.env`.

Close the tunnel when you're done.

## Next steps

- Deploy changes as described in [CI and CD](../../explanation/azure-vm/ci-cd.md).
- If SSH or Key Vault access stops working after your home IP changes, see
  [Troubleshoot: your home IP address changed](troubleshoot-home-ip-change.md).
