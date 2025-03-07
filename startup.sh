#!/bin/bash
set -e

echo "Starting deployment script..."

# Set Python path for Azure App Service
export PYTHONPATH="/home/site/wwwroot"

# Create and activate virtual environment if it doesn't exist
if [ ! -d "antenv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv antenv
fi

echo "Activating virtual environment..."
source antenv/bin/activate

# Install dependencies
echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Add gunicorn if not in requirements
pip install gunicorn pyodbc

# Apply database migrations
echo "Applying database migrations..."
export FLASK_APP=wsgi.py
flask db upgrade || echo "Warning: Database migration failed, continuing deployment..."

# Set port from environment or default to 8000
export PORT="${PORT:-8000}"
echo "Using port: $PORT"

# Start Gunicorn with our config
echo "Starting Gunicorn..."
cd /home/site/wwwroot
exec gunicorn --bind=0.0.0.0:$PORT wsgi:app
