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
