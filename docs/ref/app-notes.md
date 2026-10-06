

# Containers


## DSV-Analytics

  dsv-analytics (the Grafana image)
  - Admin password: GF_SECURITY_ADMIN_USER and GF_SECURITY_ADMIN_PASSWORD set the admin account the first time Grafana creates its
    database in the dsv-analytics-data volume.
  - Dashboard loaded at launch: src/dsv-analytics/provisioning/ is mounted into /etc/grafana/provisioning. At startup Grafana reads
    datasources/datasource.yml (the Postgres connection, using the read-only dinesafe_app role) and dashboards/dashboard.yml, which
    loads dinesafe.json. GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH makes that dashboard the home page.