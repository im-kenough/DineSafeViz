# Commands Cheat Sheet

## Docker Commands
For dev testing purposes

## Deploy app

```bash
docker compose up -d
```

### Deploy app & follow db logs

Track successful data fetch and db load
```bash
docker compose up -d && docker container logs -f dinesafeviz-init-db
docker compose up -d && docker container logs -f dinesafeviz-db-1
```

```bash
# wipes pgdata volume, clears the partial load
docker compose down -v      

# picks up changes    
docker compose build init-db
docker compose up -d

```

## Follow logs

### Follow webapp logs

```bash
docker container logs -f dinesafeviz-web-1
```

### Follow poastgres logs

```bash
docker container logs -f dinesafeviz-db-1
```

### Follow ds-dashboard logs
```bash
docker container logs -f dinesafeviz-grafana-1
```


## Destroy resources

```bash
docker compose down
docker volume rm dinesafeviz_grafana_data
docker volume rm dinesafeviz_pgdata
```


## Rebuild webapp

```bash
docker compose up --build -d
```


```bash
docker compose up --build

docker compose up --build -d
```


-----

✦ To rebuild and restart specific parts of your application, you can target the individual services defined in your
  docker-compose.yml.

  To Rebuild the Web App
  The web application is defined as the web service. Use the following command to rebuild it without affecting other
  services:

   1 docker compose build web

  To rebuild and immediately restart it:
   1 docker compose up -d --build web

  To Rebuild the Database (Ingestion Logic)
  In your configuration, the db service uses a standard Postgres image, but the logic in src/db/Dockerfile (which
  handles data seeding and refreshes) is tied to the init-db service.

  To rebuild that logic:
   1 docker compose build init-db

  Summary Table
  ┌────────────────────────┬──────────────────────────────────┐
  │ Goal                   │ Command                          │
  ├────────────────────────┼──────────────────────────────────┤
  │ Rebuild Web only       │ docker compose build web         │
  │ Rebuild Ingestion only │ docker compose build init-db     │
  │ Rebuild & Restart Web  │ docker compose up -d --build web │
  │ Rebuild everything     │ docker compose build             │
  └────────────────────────┴──────────────────────────────────┘

  Note: Since db uses a pre-built image (postgres:17.9), it doesn't "rebuild" in the Docker sense. If you change
  src/db/init.sql, you usually need to wipe the volume (docker compose down -v) for those changes to apply, as
  Postgres only runs init scripts on the very first boot.
