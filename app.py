import logging
from datetime import datetime, time, timedelta
from functools import cache
import os
import threading
from flask import Flask, current_app, g, jsonify, request, render_template
from flask_cors import CORS
from flask_login import current_user, LoginManager
from models import RentalAgreement, User, Message
from property import property_routes
from auth import auth_routes
from extensions import db, mail, migrate
from accounting import accounting_routes
from listings import listing_routes
from flask_wtf.csrf import CSRFProtect
from rentals import rental_routes
from config import Config
from dotenv import load_dotenv
from routes import main
from profiles import profile_routes
from contextlib import contextmanager
from cachetools import TTLCache
from sqlalchemy.pool import QueuePool
from flask_caching import Cache
from transaction import transaction_routes
from sqlalchemy.orm import Session
from api import api_routes
from messaging import message_routes
from openai import classify_transaction_with_azure
import pdfkit

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Load environment variables
    load_dotenv()
    
    # Basic configuration
    app.config.from_object(Config)
    app.secret_key = os.getenv('SECRET_KEY')
    
    # Security settings
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    # Database settings
    app.config['SQLALCHEMY_ECHO'] = False  # Set to False in production
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': QueuePool,
        'pool_size': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'max_overflow': 2,
        'pool_pre_ping': True
    }
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf = CSRFProtect(app)
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    
    # Configure CORS
    CORS(app, resources={r"/api/*": {"origins": ["https://propves.com"]}})
    
    # Set up login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth_routes.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            logger.error(f"Error loading user {user_id}: {e}")
            return None
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {str(e)}")
        return render_template('errors/500.html'), 500
    
    # Register blueprints
    app.register_blueprint(property_routes)
    app.register_blueprint(auth_routes, url_prefix='/auth')
    app.register_blueprint(rental_routes)
    app.register_blueprint(main)
    app.register_blueprint(profile_routes)
    app.register_blueprint(accounting_routes)
    app.register_blueprint(transaction_routes)
    app.register_blueprint(api_routes)
    app.register_blueprint(listing_routes)
    app.register_blueprint(message_routes)
    
    # Ensure upload directories exist
    upload_folder = os.path.join(app.root_path, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(app.config.get('UPLOAD_FOLDER_PROFILE', os.path.join(upload_folder, 'profiles')), exist_ok=True)
    
    return app

# Only used when running locally
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8000)