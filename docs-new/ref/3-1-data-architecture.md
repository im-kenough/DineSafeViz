# Data Architecture



### How the pipeline finds the files

`dsv-pipeline ingest` (`src/dsv-db/data.py`) reads the package through CKAN's
`package_show` API.

- Picks resources by exact name and format, not by resource ID, so a new
  resource ID doesn't break it.
- Downloads the recent CSV only when its CKAN `last_modified` is newer than
  the `source_last_modified` metadata on the newest file in the raw zone.
- Downloads the historical ZIP only when the raw zone has no complete
  historical folder, or when you pass `--historical`.
- See [Data landing zone](../../docs/explanation/data-landing-zone.md#the-etl-logic).
