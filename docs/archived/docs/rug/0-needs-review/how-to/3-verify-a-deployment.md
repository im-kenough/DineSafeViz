# Verify a deployment

This guide shows you how to confirm that the DineSafeViz stack runs correctly
after a deployment. Run these checks after each deployment. Every check must
pass before you mark the release complete.

To run the checks, first connect to the app VM with SSH.

## Start the stack

```sh
docker compose up --build -d
```

## Verify that the app responds

Run the following command. The expected result is `200`.

```sh
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
```

## Verify that the analytics proxy responds

Run the following command. The expected result is `200`.

```sh
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/analytics/api/health
```

## Verify the app routes

Run the following commands. The expected result is `200` for each route.

```sh
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/inspections
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/dashboard
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/info
```

## Verify the home page navigation links

Run the following command. The expected result is two matches.

```sh
curl -s http://localhost:8080/ | grep -o 'href="/inspections"\|href="/dashboard"'
```

## Tear down the stack

```sh
docker compose down
```
