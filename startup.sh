#!/bin/bash
set -e

echo "Starting deployment script..."

# Set Python path for Azure App Service
export PATH="/usr/local/bin:/opt/python/3.11/bin:$PATH"
export PYTHONPATH="/opt/python/3.11/lib/python3.11/site-packages:$PYTHONPATH"

# Find Python executable
for python_cmd in "python3.11" "python3" "python"; do
    if command -v $python_cmd >/dev/null 2>&1; then
        PYTHON_PATH=$(command -v $python_cmd)
        break
    fi
done

if [ -z "$PYTHON_PATH" ]; then
    echo "Error: Python not found"
    exit 1
fi

echo "Using Python at: $PYTHON_PATH"

# Create and activate virtual environment
echo "Setting up virtual environment..."
$PYTHON_PATH -m venv antenv || python -m venv antenv
source antenv/bin/activate || {
    echo "Failed to activate virtual environment"
    exit 1
}

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
exec gunicorn --config gunicorn.conf.py --bind=0.0.0.0:$PORT wsgi:application
