# Post Implementation Verification

### Start the stack
docker compose up --build -d 
 
### Verify Grafana is NOT externally accessible (expect: connection refused)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 
 
### Verify proxy works (expect: 200) 
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/analytics/api/health
 
### Verify dashboard page (expect: 200)
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/dashboard 
 
### Verify home page has dashboard link (expect: href="/dashboard")
curl -s http://localhost:5000/ | grep -o 'href="/dashboard"' 
 
### Tear down
docker compose down


---


## Step 8: Verify the installation

Check that all services are running:

```bash
docker compose ps
```

You should see all services with a status of "Up" (or "Exited" for one-shot services like `dsv-init-db`).

Test the Flask web application:

```bash
curl http://localhost:5000
```

You should receive an HTML response containing the inspection data table.

Access the web application in your browser:
- **Web app:** [http://localhost:5000](http://localhost:5000)
- **Analytics dashboard:** [http://localhost:5000/analytics/](http://localhost:5000/analytics/)
- **Direct Grafana access:** [http://localhost:3000/analytics/](http://localhost:3000/analytics/)

## Step 9: Access the analytics dashboard

The analytics dashboard is powered by Grafana and requires authentication for direct access.

Navigate to [http://localhost:3000/analytics/](http://localhost:3000/analytics/) and log in with:
- **Username:** The value of `DSV_ANALYTICS_ADMIN_USER` from your `.env` file (default: `admin`)
- **Password:** The value of `DSV_ANALYTICS_ADMIN_PASSWORD` from your `.env` file

You'll see the DineSafe analytics dashboard showing inspection statistics and trends over time. The embedded dashboard at [http://localhost:5000/analytics/](http://localhost:5000/analytics/) is anonymous and doesn't require login.



```bash
docker compose logs -f dsv-init-db
```

Watch for messages indicating successful data loading. Once you see the initialization complete, you can press `Ctrl+C` to stop following logs.
