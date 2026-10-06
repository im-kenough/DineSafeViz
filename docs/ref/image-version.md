# Images

DineSafeViz uses the following images. Use the latest LTS or stable release when possible.

- [nginx:1.31.3-alpine](https://hub.docker.com/_/nginx/tags)
  - https://nginx.org/en/download.html
- [postgres:17.10](https://hub.docker.com/_/postgres/tags)
  - https://www.postgresql.org/support/versioning/
  - https://endoflife.date/postgresql

## Grafana
- [grafana/grafana:13.2.3](https://hub.docker.com/r/grafana/grafana/tags), linux/amd64 digest `sha256:d84563330dc9d2fd2bc096d0fb96021b5319c75bf6ed555566709998e823dec4`
  - https://github.com/grafana/grafana/releases
  - Bundles grafana-postgresql-datasource 13.0.3. Use the full image, not `-slim`, which has no bundled plugin.
    See [Grafana: the bundled PostgreSQL plugin](../explanation/grafana-postgres-plugin.md).

### PostgreSQL plugin for grafana
- https://grafana.com/api/plugins/grafana-postgresql-datasource/versions
- the `PG_PLUGIN_VERSION` build argument


- [curlimages/curl:8.21.0](https://hub.docker.com/r/curlimages/curl/tags)
  - https://curl.se/download.html
- [python:3.14.6-slim-trixie](https://hub.docker.com/_/python/tags)
  - [python versions](https://www.python.org/downloads/)
  - [debian versions](https://www.debian.org/releases/)


