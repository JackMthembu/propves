#!/bin/bash
set -e

echo "Starting deployment script..."

# Set Python paths
export PYTHONPATH="/home/site/wwwroot"
export PATH="/usr/local/bin:$PATH"

# Use Azure's Python directly
echo "Using system Python..."
which python3.11 || which python3

# Install dependencies directly (no virtualenv)
echo "Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install gunicorn pyodbc

# Apply database migrations
echo "Applying database migrations..."
export FLASK_APP=wsgi.py
python3 -m flask db upgrade || echo "Warning: Database migration failed, continuing deployment..."

# Set port from environment or default to 8000
export PORT="${PORT:-8000}"
echo "Using port: $PORT"

# Start Gunicorn
echo "Starting Gunicorn..."
cd /home/site/wwwroot
exec gunicorn --bind=0.0.0.0:$PORT wsgi:app
