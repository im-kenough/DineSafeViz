# Troubleshooting

## Dashboard does not load in Firefox or Chrome

If `/dashboard` renders the page shell but the embedded Grafana view stays
blank, the browser is usually blocking the iframe. Firefox can show a message
such as "localhost:5000 will not allow Firefox to display the page if another
site has embedded it." Chrome commonly shows a refused-to-connect message in
the frame.

Grafana sends `X-Frame-Options: deny` unless embedding is enabled. This project
renders Grafana inside an iframe on `/dashboard`, so Grafana must allow
embedding.

### Fix

Set `GF_SECURITY_ALLOW_EMBEDDING: "true"` in the `grafana` service in
`docker-compose.yml`, then recreate the containers so Grafana picks up the new
setting.

```bash
docker compose up -d --build
```

After the containers restart, open `http://localhost:5000/dashboard` again in a
browser tab.


