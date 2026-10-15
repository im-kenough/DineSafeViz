# Gunicorn WSGI server configuration for the dsv-app Flask service.
#
# Runs one worker process with 4 gthread threads so a slow DB query doesn't
# block other requests. The threads share the in-process stats cache.
# preload_app=True imports the app in the master before forking the worker.
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
