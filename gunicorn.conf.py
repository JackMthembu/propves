import multiprocessing
import os

# Number of worker processes - adjust for Azure
workers = 4  # Fixed number instead of CPU-based

# Number of threads per worker
threads = 4

# Maximum requests before worker restart
max_requests = 1000
max_requests_jitter = 50

# Timeout configs
timeout = 600  # Increased for Azure
graceful_timeout = 60

# Keep the connection alive
keepalive = 5

# Log level
loglevel = 'info'

# Access log format
accesslog = '-'
errorlog = '-'

# Bind - use port from environment
port = os.getenv('PORT', '8000')
bind = f'0.0.0.0:{port}'

# Worker class
worker_class = 'sync'

# The WSGI application object name
wsgi_app = 'wsgi:application'

# Prevent worker timeout
timeout_keep_alive = 65

# Preload app for better performance
preload_app = True
