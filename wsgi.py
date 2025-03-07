# wsgi.py
import os
import sys

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Import after path is set
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()