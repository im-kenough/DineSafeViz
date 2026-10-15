# Gunicorn WSGI server configuration for the dsv-app Flask service.
#
# Runs one process with 4 gthread workers so a slow DB query doesn't block
# other requests. preload_app=True forks after the app is initialised, which
# shares the in-process stats cache and speeds up restarts under load.
# Logs go to stdout/stderr so Docker captures them without extra config.

# Worker
workers = 1
worker_class = "gthread"
threads = 4

# Timeouts
timeout = 30
graceful_timeout = 30
keepalive = 5

# Network
bind = "0.0.0.0:8000"

# Logging
accesslog = "-"
errorlog = "-"

# Startup
preload_app = True
