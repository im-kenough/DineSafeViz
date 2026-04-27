# Journal 3

## 2026-04-26 — Update docker-compose.yml to use environment variable secrets

### Context
User requested that hardcoded DB credentials in docker-compose.yml be replaced with references to environment variables from the host machine.

### Changes
- `docker-compose.yml`: replaced hardcoded `dinesafe` credential values with `${DB_USER}`, `${DB_PASSWORD}`, `${DB_NAME}` in both `db` and `web` service blocks.

### Required env vars
Set these in your shell before running `docker compose up`:
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
