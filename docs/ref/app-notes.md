

# Containers


## DSV-Analytics

  dsv-analytics (the Grafana image, grafana/grafana pinned by digest)
  - PostgreSQL plugin: the copy bundled in the image, in /usr/share/grafana/data/plugins-bundled. GF_PLUGINS_PREINSTALL_DISABLED
    stops downloads from grafana.com. The -slim variant has no bundled copy. See docs/explanation/grafana-postgres-plugin.md.
  - Admin password: GF_SECURITY_ADMIN_USER and GF_SECURITY_ADMIN_PASSWORD set the admin account the first time Grafana creates its
    database in the dsv-analytics-data volume.
  - Dashboard loaded at launch: src/dsv-analytics/provisioning/ is mounted into /etc/grafana/provisioning. At startup Grafana reads
    datasources/datasource.yml (the Postgres connection, using the read-only dinesafe_app role) and dashboards/dashboard.yml, which
    loads dinesafe.json. GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH makes that dashboard the home page.