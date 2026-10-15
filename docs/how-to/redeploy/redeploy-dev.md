# Redeploy DineSafeViz to dev

This guide redeploys the app to dev, the stack on your workstation, after
it's already set up. Dev deploys your working tree as it is, including
uncommitted changes. For a first-time setup, see
[Deploy DineSafeViz locally](../deploy-locally.md).

## Before you begin

You need `deploy/dev.env`, an Azure CLI sign-in as `dsv-ops01`, and your
home network. The deploy loads data from the `stdsvstg01` storage account,
whose firewall only allows your home IP address.

## Redeploy

Run these commands from the repository root.

1.  Confirm that you're signed in to Azure:

    ```bash
    az account show --query user.name -o tsv    # prints dsv-ops01
    ```

    If it prints anything else or fails, run `az login`.

2.  Deploy:

    ```bash
    ./scripts/deploy.sh dev
    ```

    The script rebuilds the images, restarts the stack, runs the migrations,
    and loads stg's newest data if yours is older. It ends with
    `deploy: dev is running on http://localhost:8080`.

3.  Open <http://localhost:8080> and confirm that the map loads.

## Troubleshoot

The following table lists the errors you're most likely to see on a
redeploy. For the full list, see
[Deploy DineSafeViz locally](../deploy-locally.md#troubleshoot).

| Error or symptom | Fix |
| --- | --- |
| `can't get a storage token` | Run `az login` as `dsv-ops01`. |
| `GET https://stdsvstg01... HTTP 403` | Your home IP changed. See [Troubleshoot: your home IP address changed](../azure-vm/troubleshoot-home-ip-change.md). |
