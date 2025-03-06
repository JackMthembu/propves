import multiprocessing

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Number of threads per worker
threads = 2

# Maximum requests before worker restart
max_requests = 1000
max_requests_jitter = 50

# Timeout configs
timeout = 120
graceful_timeout = 30

# Keep the connection alive
keepalive = 5

# Log level
loglevel = 'info'

# Access log format
accesslog = '-'
errorlog = '-'

# Bind
bind = '0.0.0.0:8000'

# Worker class
worker_class = 'sync'
