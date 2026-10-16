# Set DB refresh timer

## Overview

This document explains how to set the database refresh timer. When it runs, it checks the Toronto Open Data Portal for updates and pulls it into Azure Storage.

## Setting up the refresh timer

### Automatic
The time is automatically when `init-setup-vm.sh` runs

### Manual

Install the service and the timer, filling in your user, the clone path, and the environment (`stg` or `prod`):

```bash
cd ~/DineSafeViz
for f in dsv-pipeline.service dsv-pipeline.timer; do
    sed -e "s|@ADMIN_USER@|$USER|" -e "s|@REPO_DIR@|$PWD|" -e "s|@ENV@|stg|" \
    "deploy/systemd/$f" | sudo tee "/etc/systemd/system/$f" >/dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable --now dsv-pipeline.timer
```

## On demand update

Manually triggering a data refresh

```bash
sudo systemctl start dsv-pipeline.service
journalctl -u dsv-pipeline.service -n 50 --no-pager
```

If Toronto Open Data is down, or the newest data is over 10 days old, the
unit shows `failed`. The site keeps serving the data it already has.

## Validation

Confirm the next run time:

```bash
systemctl list-timers dsv-pipeline.timer
```