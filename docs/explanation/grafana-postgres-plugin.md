# Grafana: the bundled PostgreSQL plugin

Starting with Grafana 13.2, the PostgreSQL data source, which the
DineSafeViz dashboards use to read the database, is a separate plugin that
Grafana updates from grafana.com at startup. DineSafeViz runs the full
`grafana/grafana` image, which bundles a copy of the plugin, pinned by
digest, and turns the startup download off. Grafana then works without
grafana.com. This document explains what changed upstream, why the project
uses the bundled copy, and how to update it.

## What changed in Grafana 13.2

Up to Grafana 13.1, the PostgreSQL data source was compiled into Grafana. In
13.2, Grafana moved it, along with MySQL, Loki, Prometheus, and other data
sources, into a standalone plugin, `grafana-postgresql-datasource`, that's
released separately from Grafana. By default, a background installer
downloads the latest version from the grafana.com plugin catalog into
`/var/lib/grafana/plugins` every time the server starts.

Whether Grafana works when that download fails depends on the image variant.
The following table shows the linux/amd64 images for 13.2.3, checked on
October 6, 2026:

| Image | Copy in the image | Without grafana.com |
| ----- | ----------------- | ------------------- |
| `grafana/grafana:13.2.3` (`sha256:d8456333…`) | 13.0.3, in `/usr/share/grafana/data/plugins-bundled` | Runs the bundled copy |
| `grafana/grafana:13.2.3-slim` | None | No PostgreSQL data source |

The plugin is a folder of about 35 MB:

- A Go binary, `gpx_grafana_postgresql_datasource_linux_amd64`, that Grafana
  starts as a separate process. It connects to Postgres and runs the
  queries.
- The query editor's front-end files, such as `module.js`.
- `plugin.json`, which declares the plugin's ID, type, and version, and a
  signed `MANIFEST.txt` that Grafana checks before loading it.

For Grafana's description of the change, see
[PostgreSQL data source: plugin updates](https://grafana.com/docs/grafana/latest/datasources/postgres/#plugin-updates).

## How the change affects DineSafeViz

The download needs internet access, and `dsv-analytics` doesn't have it on
the VMs. In `docker-compose.vm.yml`, Grafana only joins the `backend`
network, which is `internal: true`, so it has no route to grafana.com.

- **With the `-slim` image,** the download fails, Grafana has no handler
  for the provisioned `type: postgres` data source, and the dashboards show
  no data. Grafana can still reach `dsv-db` on `backend`; it's the plugin
  that's missing, not the connection.
- **With the full image and the default settings,** Grafana falls back to
  the bundled copy, but every start tries grafana.com and logs errors. On a
  host with internet, such as a workstation, Grafana runs whatever version
  the catalog served at the last restart, so dev and the VMs can run
  different plugin versions.

## Why use the bundled copy

DineSafeViz runs the full image and sets
`GF_PLUGINS_PREINSTALL_DISABLED=true` in `docker-compose.yml`, which applies
to dev, stg, and prod. Grafana loads the bundled plugin and doesn't contact
the plugin catalog. This keeps the number of runtime dependencies down:

- **No dependency on grafana.com.** Grafana starts and serves dashboards
  even when grafana.com or its plugin catalog is down or slow.
- **The `backend` network stays internal.** Grafana serves anonymous
  visitors, so it gets no outbound internet access, the same as `dsv-app`
  and `dsv-db`.
- **Reproducible deploys.** The image digest pins both Grafana and the
  plugin version, so dev, stg, and prod run the same plugin.
- **No extra image to maintain.** The project uses the upstream image as-is,
  so there's no Dockerfile, GHCR package, or build job for Grafana.

The alternatives were weaker. The `-slim` image doesn't work offline.
Building a custom image with a newer plugin adds a build and a package to
maintain for no functional gain. Staying on Grafana 13.1 only delays the
change. Adding `dsv-analytics` to the `egress` network would give an
internet-facing service outbound access to fix a startup download.

On the VMs, `docker-compose.vm.yml` also turns off Grafana's update check
and usage reporting. With those settings, Grafana makes no calls to
grafana.com at all.

## Plugins already in the volume

Grafana prefers a plugin in `/var/lib/grafana/plugins` over the bundled copy,
and logs `Skipping loading of plugin as it's a duplicate` for the bundled
one. `/var/lib/grafana` is the `dsv-analytics-data` volume, so a plugin that
an earlier Grafana 13.2 downloaded stays in use, at its old version, after
you turn the download off.

The VMs' volumes never had internet access, so they hold no downloaded
plugins. A dev volume that ran Grafana 13.2 with the default settings does.
[Deploy DineSafeViz locally](../how-to/deploy-locally.md#troubleshoot)
covers the one-time cleanup.

## Memory use

Running the plugin as its own process adds about 20 MiB. Measured idle with
the data source connected on October 6, 2026, Grafana 13.1 used about
223 MiB and 13.2.3 used about 242 MiB, so `docker-compose.vm.yml` raises the
memory limit for `dsv-analytics` from 256 MiB to 320 MiB.

## How the plugin gets updated

The plugin version changes only when the Grafana image changes. Dependabot's
`docker-compose` ecosystem opens PRs for new Grafana tags in
`docker-compose.yml`, and each update goes through a pull request and stg
like any other dependency. The weekly Trivy rescan in `images.yml` scans the
pinned Grafana image, including the bundled plugin.

Before you merge a Grafana update, confirm that the new image still bundles
the plugin. Run the following on your workstation, with the new image
reference:

```bash
docker run --rm --entrypoint sh grafana/grafana:<tag>@sha256:<digest> -c \
  'grep "\"version\"" /usr/share/grafana/data/plugins-bundled/grafana-postgresql-datasource/plugin.json'
```

The command prints the bundled plugin's version. If it prints
`No such file or directory`, the image doesn't bundle the plugin, and
Grafana can't read the database on the VMs.

## Related documents

- [Deploy DineSafeViz locally](../how-to/deploy-locally.md)
- [Deploy DineSafeViz to stg](../how-to/azure-vm/deploy-stg.md)
- [CI and CD for the Azure VM deployment](azure-vm/ci-cd.md)
- [App architecture](../ref/app-architecture.md)
