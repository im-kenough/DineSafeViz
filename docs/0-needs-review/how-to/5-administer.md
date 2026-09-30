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

### Migrate an existing database to split address columns

The `inspections` table stores each address in the raw
`establishment_address` column and in three split columns: `street`, `unit`,
and `postal_code`. The `dsv-init-db` container fills the split columns at
ingest. `init.sql` only runs on an empty `dsv-db-data` volume, so a database
created before these columns existed doesn't have them. The new web app fails
on `/inspections` until you add them.

To migrate the database without deleting the volume, follow these steps. The
roles, grants, and analytics dashboard data stay in place. The `/inspections`
page is empty from step 1 until the seed in step 2 finishes.

1. Add the columns and clear the table. You must do this before you deploy
   the new web app.

   ```bash
   docker compose exec dsv-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "ALTER TABLE inspections ADD COLUMN street TEXT, ADD COLUMN unit TEXT, ADD COLUMN postal_code TEXT; TRUNCATE inspections;"'
   ```

2. Rebuild and redeploy. The init container sees an empty table and runs a
   full seed. Wait for `Seed complete.` in the logs.

   ```bash
   docker compose up --build -d && docker container logs -f dsv-dsv-init-db-1
   ```

3. Restart the web app. The home page caches its counts for five days, and
   they might have been cached while the table was empty.

   ```bash
   docker compose restart dsv-app
   ```

4. Check the result. Both counts must be `0`.

   ```bash
   docker compose exec dsv-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) FILTER (WHERE establishment_address IS NOT NULL AND street IS NULL) AS missing_street, count(*) FILTER (WHERE concat(street, unit, postal_code) LIKE '"'"'%None%'"'"') AS literal_none FROM inspections;"'
   ```

For a local environment where you don't need to keep the analytics dashboard
data, use [Reset a partial database load](#reset-a-partial-database-load)
instead.

Each daily refresh logs `Unparsed recent addresses: N`. A value above `0`
means the upstream address format changed. Those rows keep the full address
in `street`, so the page still displays it.

### Rename the infraction category column

The `infraction_category` column holds the recent feed's `deficiencyDesc`
value, for example `05. MAINTENANCE / SANITATION`. Databases created before
this change call it `inspection_observation`. `init.sql` only runs on an empty
`dsv-db-data` volume, so you must rename the column by hand. Until you do, the
new web app fails on `/inspections`, the daily refresh fails, and three
analytics dashboard panels show errors.

The rename only changes the column name. It keeps the data, roles, and
grants, so you don't need to reseed.

To rename the column, follow these steps:

1. Rename the column. Run this right before you deploy, because the old web
   app fails on `/inspections` from this point until the new one is running.

   ```bash
   docker compose exec dsv-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "ALTER TABLE inspections RENAME COLUMN inspection_observation TO infraction_category;"'
   ```

2. Rebuild and redeploy.

   ```bash
   docker compose up --build -d
   ```

3. Check the result. The query returns the most common infraction
   categories.

   ```bash
   docker compose exec dsv-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT infraction_category, count(*) FROM inspections GROUP BY 1 ORDER BY 2 DESC LIMIT 5;"'
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
