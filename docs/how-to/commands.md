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
docker compose up -d && docker container logs -f dsv-dsv-init-db-1
docker compose up -d && docker container logs -f dsv-dsv-db-1
```

```bash
# wipes dsv-db-data volume, clears the partial load
docker compose down -v      

# picks up changes    
docker compose build dsv-init-db
docker compose up -d

```

## Follow logs

### Follow app logs

```bash
docker container logs -f dsv-dsv-app-1
```

### Follow PostgreSQL logs

```bash
docker container logs -f dsv-dsv-db-1
```

### Follow analytics logs
```bash
docker container logs -f dsv-dsv-analytics-1
```


## Destroy resources

```bash
docker compose down
docker volume rm dsv_dsv-analytics-data
docker volume rm dsv_dsv-db-data
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
  The web application is defined as the `dsv-app` service. Use the following command to rebuild it without affecting other
  services:

   1 docker compose build dsv-app

  To rebuild and immediately restart it:
   1 docker compose up -d --build dsv-app

  To Rebuild the Database (Ingestion Logic)
  In your configuration, the `dsv-db` service uses a standard Postgres image, but the logic in `src/dsv-db/Dockerfile` (which
  handles data seeding and refreshes) is tied to the `dsv-init-db` service.

  To rebuild that logic:
   1 docker compose build dsv-init-db

  Summary Table
  ┌────────────────────────┬──────────────────────────────────┐
  │ Goal                   │ Command                          │
  ├────────────────────────┼──────────────────────────────────┤
  │ Rebuild Web only       │ docker compose build dsv-app         │
  │ Rebuild Ingestion only │ docker compose build dsv-init-db     │
  │ Rebuild & Restart Web  │ docker compose up -d --build dsv-app │
  │ Rebuild everything     │ docker compose build             │
  └────────────────────────┴──────────────────────────────────┘

  Note: Since `dsv-db` uses a pre-built image (postgres:17.9), it doesn't "rebuild" in the Docker sense. If you change
  src/dsv-db/init.sql, you usually need to wipe the volume (docker compose down -v) for those changes to apply, as
  Postgres only runs init scripts on the very first boot.
