#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Apply database migrations
flask db upgrade

# Start Gunicorn with our config
gunicorn --config gunicorn.conf.py wsgi:app
