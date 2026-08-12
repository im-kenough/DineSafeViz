# Administer DineSafeViz

This document contains two parts. The first part shows you how to log in to the
analytics dashboard. The second part is a reference of the Docker commands that
you use during local development and testing.

## Log in to the analytics dashboard

The analytics dashboard reads data from the PostgreSQL database. It presents
that data through the embedded dashboard stack. To log in, follow these steps.

1. Open `http://localhost:3000/analytics/`.
2. Log in with the `DSV_ANALYTICS_ADMIN_USER` and
   `DSV_ANALYTICS_ADMIN_PASSWORD` values from the `.env` file.

## Docker command reference

Use the following commands during local development and testing.

### Deploy the app

```bash
docker compose up -d
```

### Deploy the app and follow the database logs

To track a successful data fetch and database load, follow the init or database
container logs.

```bash
docker compose up -d && docker container logs -f dsv-dsv-init-db-1
docker compose up -d && docker container logs -f dsv-dsv-db-1
```

### Reset a partial database load

If a database load stops partway, reset it. The first command deletes the
`dsv-db-data` volume and clears the partial load. The next two commands rebuild
the init container and start the stack again.

```bash
docker compose down -v
docker compose build dsv-init-db
docker compose up -d
```

### Follow the container logs

```bash
docker container logs -f dsv-dsv-app-1
docker container logs -f dsv-dsv-db-1
docker container logs -f dsv-dsv-analytics-1
```

### Destroy the resources

```bash
docker compose down
docker volume rm dsv_dsv-analytics-data
docker volume rm dsv_dsv-db-data
```

### Rebuild the web app

```bash
docker compose up --build -d
```
