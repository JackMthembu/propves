from datetime import timedelta
from functools import cache
import os
from flask import Flask, current_app, jsonify, render_template, session, g, request
from flask_cors import CORS
from flask_login import current_user, login_required
from flask_migrate import Migrate
from models import Country, User, State 
from property import property_routes
from auth import auth_routes
from extensions import db, mail, login_manager, migrate
from subscriptions import subscription_routes
from accounting import accounting_routes
# from listings import listing_routes
from wishlist import wishlist_routes
# from scheduling import calendar_routes
from flask_wtf.csrf import CSRFProtect
from rentals import rental_routes
from config import Config
from dotenv import load_dotenv
from routes import main
from profiles import profile_routes
import logging
from contextlib import contextmanager
from cachetools import TTLCache
from sqlalchemy.pool import QueuePool
from flask_caching import Cache
from transaction import transaction_routes
from sqlalchemy.orm import Session
from api import api_routes

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

request_cache = TTLCache(maxsize=100, ttl=5)  # 5-second cache for requests

# Initialize cache

cache = Cache(config={
    'CACHE_TYPE': 'simple'  # For development. Use 'redis' or 'memcached' in production
})

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = db.session
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def create_app():
    app = Flask(__name__, 
        template_folder='templates'
    )

    load_dotenv()  

    app.config.from_object(Config)
    
    # Add Google Maps API key configuration here
    app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not app.config['GOOGLE_MAPS_API_KEY']:
        app.logger.warning("Google Maps API key not found in environment variables")
        if app.debug:
            app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY')
            
    
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': QueuePool,
        'pool_size': 10,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'max_overflow': 2
    }

    csrf = CSRFProtect()
    csrf.init_app(app)
    
    if not os.path.exists(app.config['UPLOAD_FOLDER_PROFILE']):
        os.makedirs(app.config['UPLOAD_FOLDER_PROFILE'])

    CORS(app, resources={r"/api/*": {"origins": ["https://propves.com"]}})

    db.init_app(app) 
    mail.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth_routes.login'

    app.register_blueprint(property_routes)
    app.register_blueprint(auth_routes, url_prefix='/auth')
    app.register_blueprint(subscription_routes)
    app.register_blueprint(wishlist_routes)
    app.register_blueprint(rental_routes)
    app.register_blueprint(main)
    app.register_blueprint(profile_routes)
    app.register_blueprint(accounting_routes, url_prefix='/accounting')
    app.register_blueprint(transaction_routes)
    app.register_blueprint(api_routes)

    cache.init_app(app)

    # Add user loader
    @login_manager.user_loader
    def load_user(user_id):
        try:
            with app.app_context():
                session = Session(db.engine)
                user = session.get(User, int(user_id))
                logger.debug(f"Loading user {user_id}: {'Found' if user else 'Not found'}")
                if user:
                    logger.debug(f"User authenticated: {user.is_authenticated}")
                    logger.debug(f"User active: {user.is_active}")
                return user
        except Exception as e:
            logger.error(f"Error loading user {user_id}: {str(e)}")
            return None

    @app.template_filter('format_currency')
    def format_currency(value):
        if value is None:
            return '$0.00'
        return f'${value:,.2f}'
    
    @app.template_filter('currency')
    def currency_filter(value):
        try:
            return f"${value:,.2f}"
        except (ValueError, TypeError):
            return "$0.00"

    # Debug middleware
    @app.before_request
    def before_request():
        if not request.endpoint:
            return
        
        # Skip authentication for static files
        if request.endpoint.startswith('static'):
            return

        # Check cache first
        cached_user = get_cached_user() if current_user.is_authenticated else None
        if cached_user:
            g.user = cached_user
            return

        # Only authenticate for non-static requests
        if current_user.is_authenticated:
            session = Session(db.engine)
            user = session.get(User, current_user.get_id())
            if user:
                g.user = user
                cache_key = f"user_{request.endpoint}_{user.id}"
                request_cache[cache_key] = user
                current_app.logger.debug(f"User authenticated: {user.id}")

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    # Create upload directories if they don't exist
    os.makedirs(app.config['UPLOAD_FOLDER_PROFILE'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_PROPERTY'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_DOCUMENTS'], exist_ok=True)

    print(app.url_map)

    # Set a secure secret key
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secure-secret-key')
    
    # CSRF Configuration
    csrf.init_app(app)
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_CHECK_DEFAULT'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600
    
    # Add this near other app.config settings
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'temp'), exist_ok=True)
    
    return app

def get_cached_user():
    """Get user from cache or database."""
    user_id = current_user.id
    cache_key = f'user_{user_id}'
    
    # Try to get from cache first
    cached = cache.get(cache_key)
    if cached:
        return cached
        
    # If not in cache, get from DB using Session.get() (new SQLAlchemy 2.0 style)
    with app.app_context():
        session = Session(db.engine)
        user = session.get(User, user_id)
        if user:
            cache.set(cache_key, user, timeout=300)  # Cache for 5 minutes
        return user

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # app.run(debug=True)
        app.run(debug=True, port=5001)
        # app.run(host='0.0.0.0', port=8000)