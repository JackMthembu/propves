#!/bin/bash
set -e

echo "Starting deployment script..."

# Set Python path for Azure App Service
export PYTHON_PATH="/usr/local/bin/python3.11"
if [ ! -f "$PYTHON_PATH" ]; then
    PYTHON_PATH="/opt/python/3.11/bin/python3.11"
fi
if [ ! -f "$PYTHON_PATH" ]; then
    PYTHON_PATH=$(which python3.11 || which python3 || which python)
fi

if [ -z "$PYTHON_PATH" ]; then
    echo "Error: Python not found"
    exit 1
fi

echo "Using Python at: $PYTHON_PATH"

# Create and activate virtual environment if it doesn't exist
if [ ! -d "antenv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_PATH -m venv antenv
fi

echo "Activating virtual environment..."
source antenv/bin/activate || {
    echo "Failed to activate virtual environment"
    exit 1
}

# Install dependencies
echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt || {
    echo "Failed to install dependencies"
    exit 1
}

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
exec gunicorn --config gunicorn.conf.py --bind=0.0.0.0:$PORT wsgi:app
