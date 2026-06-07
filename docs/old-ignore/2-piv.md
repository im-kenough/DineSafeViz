# Post implementation verification

Run these commands after each deployment to confirm the stack is healthy.
All checks must pass before marking the release complete.

### Start the stack

```sh
docker compose up --build -d
```

### Verify the app is up (expect: 200)

```sh
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/
```

### Verify the analytics proxy works (expect: 200)

```sh
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/analytics/api/health
```

### Verify all app routes (expect: 200 for each)

```sh
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/inspections
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/dashboard
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/info
```

### Verify home page navigation links (expect: two matches)

```sh
curl -s http://localhost:5000/ | grep -o 'href="/inspections"\|href="/dashboard"'
```

### Tear down

```sh
docker compose down
```
