# wsgi.py
import os
import sys

# Get the absolute path of the project directory
project_dir = os.path.dirname(os.path.abspath(__file__))

# Add project directory to Python path if not already there
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import the Flask application factory
from app import create_app

# Create the application instance
application = create_app()
app = application  # For compatibility with both Gunicorn and Azure

if __name__ == "__main__":
    application.run()