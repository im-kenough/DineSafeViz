
# How to log in to the DineSafeViz analytics dashboard

The analytics dashboard reads data from the PostgreSQL database and presents
it through the embedded dashboard stack.

- Open `http://localhost:3000/analytics/`.
- Log in with `DSV_ANALYTICS_ADMIN_USER` and
  `DSV_ANALYTICS_ADMIN_PASSWORD` from `.env`.


---

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