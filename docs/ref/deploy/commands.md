# Commands Cheat Sheet

## Docker Commands
For dev testing purposes

## Deploy app

```bash
docker compose up -d
```

## Follow logs

### Follow poastgres logs
```bash
docker container logs -f dinesafeviz_pgdata
```

### Follow ds-dashboard logs
```bash
docker container logs -f dinesafeviz_grafana_data
```


## Destroy resources

```bash
docker compose down
docker volume rm dinesafeviz_grafana_data dinesafeviz_pgdata
```


## Rebuild webapp

```bash
docker compose up --build -d
```