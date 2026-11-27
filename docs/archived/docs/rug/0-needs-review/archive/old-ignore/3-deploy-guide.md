# Deployment

Instructions on how to deploy the application to existing infrastructure. Ex: redeploying an app

# Redeploy full app

## Tear down docker stack

```bash
# Navigate to the app directory
cd ~/app/DineSafeViz

# bring down docker, delete volumes declared in docker-compose.yml
docker compose down -v

# delete all docker images
docker rmi $(docker images -a -q)
```

## Delete the repo

```bash
cd ..
rm -rf DineSafeViz/
```

## Clone down the repo

```bash
git clone git@github.com:im-kenough/DineSafeViz.git
cd DineSafeViz
```

> [!NOTE]
> You'll be on the default branch. If you want to access a different branch use:
> 
> ```git fetch --all```
> 
> ```git switch some-other-branch```

## Configure environment variables

The application reads configuration from a `.env` file. Copy the example configuration:

```bash
cp .env.example .env
```

Edit the `.env` file with `nano`:

```bash
nano .env
```

Update the variables based on your deployment environment. For a local test installation, most defaults are suitable. If you need to customize database credentials, API keys, or ports, make those changes now. Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

## Build and start the application

Start all services using Docker Compose:

```bash
docker compose up -d
```

The `-d` flag runs services in the background (detached mode).

This command will:
1. Build Docker images for custom services (Flask app and database initialization scripts)
2. Pull pre-built images (PostgreSQL, Grafana)
3. Create and start all containers
4. Initialize the database and load the CSV data
5. Configure the Grafana analytics dashboard