#!/bin/bash
set -e

echo "Starting deployment script..."

# Set environment variables
export PORT="${PORT:-8000}"
export FLASK_APP=wsgi.py
export FLASK_ENV=production
export PYTHONPATH="/home/site/wwwroot"

# Debug information
echo "Current directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Contents of current directory:"
ls -la

# Install dependencies
echo "Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install gunicorn pyodbc

# Apply database migrations
echo "Applying database migrations..."
python -m flask db upgrade || echo "Warning: Database migration failed, continuing deployment..."

# Start Gunicorn
echo "Starting Gunicorn on port: $PORT"
exec python -m gunicorn \
    --bind=0.0.0.0:$PORT \
    --timeout 600 \
    --workers 4 \
    --threads 2 \
    --access-logfile '-' \
    --error-logfile '-' \
    --log-level debug \
    wsgi:application
