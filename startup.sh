#!/bin/bash
set -e

echo "Starting deployment script..."

# Create and activate virtual environment
echo "Setting up virtual environment..."
python -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Add gunicorn if not in requirements
pip install gunicorn

# Apply database migrations
echo "Applying database migrations..."
export FLASK_APP=wsgi.py
flask db upgrade || echo "Warning: Database migration failed, continuing deployment..."

# Start Gunicorn with our config
echo "Starting Gunicorn..."
gunicorn --config gunicorn.conf.py wsgi:application
