#!/bin/bash
set -e

echo "Starting deployment script..."

# Set Python paths and environment variables
export PYTHONPATH="/home/site/wwwroot"
export PATH="/usr/local/bin:$PATH"
export PORT="${PORT:-8000}"

# Ensure we're in the correct directory
cd /home/site/wwwroot

# Use Azure's Python directly
echo "Using system Python..."
python_cmd=$(which python3.11 || which python3)
echo "Using Python: $python_cmd"

# Install dependencies directly (no virtualenv)
echo "Installing dependencies..."
$python_cmd -m pip install --upgrade pip
$python_cmd -m pip install -r requirements.txt
$python_cmd -m pip install gunicorn pyodbc

# Apply database migrations
echo "Applying database migrations..."
export FLASK_APP=wsgi.py
$python_cmd -m flask db upgrade || echo "Warning: Database migration failed, continuing deployment..."

echo "Starting Gunicorn on port: $PORT"
exec gunicorn \
    --bind=0.0.0.0:$PORT \
    --timeout 600 \
    --access-logfile '-' \
    --error-logfile '-' \
    --log-level info \
    wsgi:app
