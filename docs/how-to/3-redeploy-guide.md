# Redeploy the application

This guide shows you how to redeploy the application to existing
infrastructure. Choose the case that matches your goal.

## Redeploy the latest code and keep the data

To redeploy the latest code to the running instance and keep the existing
Docker volumes, run the following command.

```bash
make redeploy-app-keep-data
```

This command destroys the app but keeps the Docker volumes. It then reclones
the repository, templates the `.env` file, and runs `docker compose up`.

## Redeploy the latest code and reset the data

To redeploy the latest code to the running instance and delete the existing
Docker volumes, run the following command. Deleting the volumes triggers a
fresh initialization.

```bash
make redeploy-app
```

## Redeploy to a new instance

To redeploy the latest code to a new instance, run the following command.

```bash
make down && make up
```

This command deletes the app and the VM. It then provisions another VM and
deploys the app.
