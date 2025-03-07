#config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Define GOOGLE_MAPS_API_KEY at module level
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Celery configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')  
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')  
    
    # Database configuration
    DB_USERNAME = os.getenv('DB_USERNAME')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_SERVER = os.getenv('DB_SERVER')
    DB_NAME = os.getenv('DB_NAME')

    # Use SQL Server if credentials are provided, otherwise fallback to SQLite
    if all([DB_USERNAME, DB_PASSWORD, DB_SERVER, DB_NAME]):
        SQLALCHEMY_DATABASE_URI = (
            f"mssql+pyodbc://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}"
            "?driver=ODBC+Driver+17+for+SQL+Server"
            "&TrustServerCertificate=yes"
            "&Encrypt=yes"
        )
        
        # SQLAlchemy configuration
        SQLALCHEMY_ECHO = True
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': 20,
            'pool_timeout': 30,
            'pool_recycle': 1800,
            'pool_pre_ping': True
        }
    else:
        print("Warning: Using SQLite as fallback database")
        SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://propvesdb:vowhY1-vinnug-wepkyb@lethabo.database.windows.net/green-mammba?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes&Encrypt=yes'
    
    # General configuration
    DEBUG = True
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.getenv('WTF_CSRF_SECRET_KEY')
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail configuration
    MAIL_SERVER = 'kassandra.aserv.co.za'  
    MAIL_PORT = 587  
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'hello@propves.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('Propves', 'hello@propves.com')
    MAIL_DEBUG = True
    MAIL_SUPPRESS_SEND = False
    MAIL_MAX_EMAILS = 50
    
    # Upload folders configuration
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    UPLOAD_FOLDER_PROFILE = os.path.join(UPLOAD_FOLDER, 'profile_pictures')
    UPLOAD_FOLDER_PROPERTY = os.path.join(UPLOAD_FOLDER, 'property_images')
    UPLOAD_FOLDER_DOCUMENTS = os.path.join(UPLOAD_FOLDER, 'documents')
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Azure OpenAI Configuration
    AZURE_API_KEY = os.environ.get("AZURE_API_KEY")
    AZURE_API_ENDPOINT = os.environ.get("AZURE_API_ENDPOINT")
    AZURE_DEPLOYMENT_NAME = os.environ.get("AZURE_DEPLOYMENT_NAME")
    AZURE_MODEL_NAME = os.environ.get("AZURE_MODEL_NAME")