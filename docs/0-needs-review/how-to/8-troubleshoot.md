# Troubleshoot

## Dashboard does not load in Firefox or Chrome

If `/dashboard` renders the page shell but the embedded Grafana view stays
blank, the browser is usually blocking the iframe. Firefox can show a message
such as "localhost:8080 will not allow Firefox to display the page if another
site has embedded it." Chrome commonly shows a refused-to-connect message in
the frame.

Grafana sends `X-Frame-Options: deny` unless embedding is enabled. This
project renders the analytics dashboard inside an iframe on `/dashboard`, so
Grafana must allow embedding.

### Fix

Set `GF_SECURITY_ALLOW_EMBEDDING: "true"` in the `dsv-analytics` service in
`docker-compose.yml`. Then recreate the containers so that Grafana picks up
the new setting.

```bash
docker compose up -d --build
```

After the containers restart, open `http://localhost:8080/dashboard` again in
a browser tab.

## Dashboard shell loads but shows no data

An ad blocker or content blocker can block the requests that load data from
PostgreSQL, even though the dashboard shell renders. Observed behavior with
uBlock Origin and other blockers enabled:

- Firefox normal mode: does not load the data
- Firefox private mode: loads
- Chrome normal mode: loads
- Chrome incognito mode: loads

### Fix

If the dashboard shell renders but no data appears, disable your ad blocker
for the site. Alternatively, open the page in a private or incognito window.

## Services fail to start

Check the logs for each service to identify the issue.

```bash
docker compose logs dsv-db
docker compose logs dsv-app
docker compose logs dsv-analytics
```

### Fix

Match the log output to one of these common issues.

- **Port conflicts:** If port 8080 or 3000 is already in use, stop the
  conflicting service or edit `docker-compose.yml` to use different ports.
- **Insufficient disk space:** Make sure that your system has at least 5 GB of
  free disk space.
- **Database initialization timeout:** If the database takes longer than
  expected to initialize, check the `dsv-init-db` logs.

## Database does not initialize

If the PostgreSQL database fails to load the CSV data, the database volume
likely holds a partial or stale load.

### Fix

Run the following commands.

```bash
docker compose down -v
docker compose up -d
```

This command removes the existing database volume and restarts from scratch.
The `-v` flag removes named volumes.

## Cannot connect to the database

### Fix

Verify that the database is running.

```bash
docker compose ps dsv-db
```

The `dsv-db` service should show "Up (healthy)". If it shows "(unhealthy)" or
"Exited", check the logs.

```bash
docker compose logs dsv-db
```

## Analytics dashboard does not load

The Grafana dashboard might take 30 seconds to initialize.

### Fix

Wait a moment, and then refresh your browser. If it still does not load,
check the logs.

```bash
docker compose logs dsv-analytics
docker compose logs dsv-init-analytics
```

## Port already in use

If you see an error such as "Bind for 0.0.0.0:8080 failed," another process
is using that port.

### Fix

You have two options: stop the conflicting process, or change the port in
`docker-compose.yml`.

To change the port, open the file.

```bash
nano docker-compose.yml
```

Find the `ports` section for the `dsv-nginx` service, and then change
`8080:80` to another host port, such as `8081:80`. Then restart the stack.

```bash
docker compose up -d
```

## Known issues

Documented behavioral quirks in the IaC build toolchain (Packer, Ansible,
Proxmox) that are not bugs to fix but constraints to work around. Each entry
explains the symptom, root cause, and the applied mitigation.

### Packer ansible provisioner: SFTP file transfer fails silently

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
local proxy it manages. This proxy only handles exec channels, so it does not
implement the SFTP subsystem. Ansible's `Gathering Facts` step must upload
`AnsiballZ_setup.py` to the remote host over SFTP before it can run any
tasks. That upload fails silently through the proxy, producing a blank error
message.

### Fix

All three Packer templates set `use_proxy = false` on the ansible
provisioner. This causes Packer to pass the real VM IP address and an
ephemeral SSH key directly to `ansible-playbook`. Ansible then manages its own
SSH connection, including SFTP. This works because the Packer host has direct
LAN access to the build VMs on `10.0.20.0/24`.

**Constraint:** `use_proxy = false` requires the Packer host to have direct
network reachability to the build VM. If the build environment changes, for
example Packer running in a CI runner with no direct VM access, the proxy
limitation needs a different workaround, such as an `sftp_command` override
or a bastion.
