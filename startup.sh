#!/bin/bash
set -e

echo "Starting deployment script..."

# Set Python path for Azure App Service
export PATH="/usr/local/bin:/opt/python/3.11/bin:$PATH"
export PYTHONPATH="/opt/python/3.11/lib/python3.11/site-packages:$PYTHONPATH"

# Find Python executable
PYTHON_PATH=$(which python3 || which python)
if [ -z "$PYTHON_PATH" ]; then
    echo "Error: Python not found"
    exit 1
fi

echo "Using Python at: $PYTHON_PATH"

# Create and activate virtual environment
echo "Setting up virtual environment..."
$PYTHON_PATH -m venv antenv || python -m venv antenv
source antenv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Add gunicorn if not in requirements
pip install gunicorn pyodbc

# Install ODBC driver if not present
if ! dpkg -l | grep -q "msodbcsql17"; then
    echo "Installing ODBC driver..."
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - || true
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list || true
    apt-get update || true
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 || true
fi

# Apply database migrations
echo "Applying database migrations..."
export FLASK_APP=wsgi.py
flask db upgrade || echo "Warning: Database migration failed, continuing deployment..."

# Start Gunicorn with our config
echo "Starting Gunicorn..."
exec gunicorn --config gunicorn.conf.py wsgi:application
