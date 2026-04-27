# Post Implementation Verification

### Start the stack
docker compose up --build -d 
 
### Verify Grafana is NOT externally accessible (expect: connection refused)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 
 
### Verify proxy works (expect: 200) 
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/grafana/api/health
 
### Verify dashboard page (expect: 200)
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/dashboard 
 
### Verify home page has dashboard link (expect: href="/dashboard")
curl -s http://localhost:5000/ | grep -o 'href="/dashboard"' 
 
### Tear down
docker compose down