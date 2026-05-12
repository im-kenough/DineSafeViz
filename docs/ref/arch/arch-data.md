# Data Architecture

This document discusses the data components of the DineSafeViz application

ToDO: show a chart illustrating the high level data components

# Data Services

## Database

The webapp and analytics services pulls data from a postgresql db.

A bulk dataload is performed when the app is first created. In the future, a scheduled Github action will run to refresh the data

### Datasource

We pull the data from the City of Toronto Open Data portal as csv files. There's also an API. The data comes in two parts:
- Historical data: 2001- 2023
- Current data: 2023 - present, refreshed daily by the City.

> [!Note]
> There is a gap in the data between **2023-01-01 through 2023-11-09** (~11 months). This is a data quality issue, this data is missing from the Toronto Open Data portal.

See [data mapping](docs/ref/data.md) for more details.


#### Historical Data columns

Show a sample 6 rows + the column header. Select rows that have most columns populated. Output as a readable markdown table.

#### Current Data columns

Show a sample 6 rows + the column header. Select rows that have most columns populated. Output as a readable markdown table.

### Database schema

list the db name, table name.
output schema as a readable markdown table.

## DineSaveViz Inspections

The web app pulls from the database and creates a human friendly report showing the inspection results.

Describe how it works, where the code is stored. point out relevant files and briefly describe what it does


## DineSafeViz Analytics

The DineSafeViz Analytics Dashboard breaks down the dataset and visualises them in a grafana dashboard

It reads from the postgresql database and renders a dashboard.


- src/dsv-analytics/provisioning/datasources/datasource.yml: the dashboard's data source configuration.
- src/grafana/provisioning/dashboards/dashboard.yml: dashboard configruation in grafana
- src/dsv-analytics/provisioning/dashboards/dinesafe.json: actual dashboard versioned controlled as code




# Data Operations

## Data ingestion

Explain how the data is fetched, where it's stored.

### Data sanitization

The following data sanitization is done before loading into the database.

- A.
- B.
- C.

Future:
- https://github.com/im-kenough/DineSafeViz/issues/76
- https://github.com/im-kenough/DineSafeViz/issues/11
- https://github.com/im-kenough/DineSafeViz/issues/13


## Data refresh

A database refresh happens when...
