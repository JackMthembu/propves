# app.py
from datetime import datetime, time, timedelta
from functools import cache
import os
import threading
from flask import Flask, current_app, g, jsonify, request
from flask_cors import CORS
from flask_login import current_user, LoginManager
# import celery_config
from models import RentalAgreement, User, Message
from property import property_routes
from auth import auth_routes
from extensions import db, mail, migrate
# from subscriptions import subscription_routes
from accounting import accounting_routes
from listings import listing_routes
# from wishlist import wishlist_routes
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
from messaging import message_routes
# from celery.schedules import crontab  
# from tenant import tenant_routes
from openai import classify_transaction_with_azure
import pdfkit

app = Flask(__name__)  
app.secret_key = os.getenv('SECRET_KEY') 

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

request_cache = TTLCache(maxsize=100, ttl=5)  

logging.basicConfig(level=logging.INFO)

def scheduled_task():
    try:
        logging.info(f"Scheduled task is running at {datetime.now()}")

    except Exception as e:
        logging.error(f"Error occurred: {e}")

    @app.before_first_request
    def scheduled_task():
        def run_updates():
            with app.app_context():
                while True:
                    try:
                        update_expired_agreements()
                    except Exception as e:
                        logging.error(f"Error updating expired agreements: {e}")
                    time.sleep(600)  # 600 seconds = 10 minutes

        thread = threading.Thread(target=run_updates)
        thread.start()

# Initialize cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})  # You can choose other cache types as needed

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

@cache.memoize(timeout=60)  # Cache the result for 60 seconds
def get_cached_user(user_id):
    return User.query.get(user_id)  # Example of fetching a user from the database

def create_app():
    app = Flask(__name__, template_folder='templates')

    load_dotenv()

    app.config.from_object(Config)
    app.config.update(
        CELERY_BROKER_URL=os.getenv('CELERY_BROKER_URL'),
        CELERY_RESULT_BACKEND=os.getenv('CELERY_RESULT_BACKEND'),
        API_NINJA_API_KEY=os.getenv('API_NINJA_API_KEY'),
        GOOGLE_MAPS_API_KEY=os.getenv('GOOGLE_MAPS_API_KEY'),
        SECRET_KEY=os.getenv('SECRET_KEY')
    )

    # from celery_config import make_celery  
    # celery = make_celery(app)

    # Add Google Maps API key configuration here
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
        'pool_size': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'max_overflow': 2,
        'pool_pre_ping': True
    }

    csrf = CSRFProtect()
    csrf.init_app(app)

    if not os.path.exists(app.config['UPLOAD_FOLDER_PROFILE']):
        os.makedirs(app.config['UPLOAD_FOLDER_PROFILE'])

    CORS(app, resources={r"/api/*": {"origins": ["https://propves.com"]}})

    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth_routes.login'

    app.register_blueprint(property_routes)
    app.register_blueprint(auth_routes, url_prefix='/auth')
    # app.register_blueprint(subscription_routes)
    # app.register_blueprint(wishlist_routes)
    app.register_blueprint(rental_routes)
    app.register_blueprint(main)
    app.register_blueprint(profile_routes)
    app.register_blueprint(accounting_routes)
    app.register_blueprint(transaction_routes)
    app.register_blueprint(api_routes)
    app.register_blueprint(listing_routes)
    app.register_blueprint(message_routes)
    # app.register_blueprint(tenant_routes, url_prefix='/tenant')

    # cache.init_app(app)
    # celery.conf.beat_schedule = {
    #     'check-incomplete-properties-every-24-hours': {
    #         'task': 'tasks.check_incomplete_properties',
    #         'schedule': crontab(hour='*', minute=0),  
    #     },
    # }

    # Celery configuration
    # celery_config.beat_schedule = {
    #     'check-incomplete-properties-every-24-hours': {
    #         'task': 'tasks.check_incomplete_properties',
    #         'schedule': crontab(hour='*', minute=0),  # Every hour at minute 0
    #     },
    # }

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

    @app.route('/classify_transaction/<item_name>', methods=['GET'])
    def classify_transaction(item_name):
        classification = classify_transaction_with_azure(item_name)
        return jsonify({"item_name": item_name, "classification": classification})

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
        cached_user = get_cached_user(current_user.id) if current_user.is_authenticated else None
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

    # CSRF Configuration
    csrf.init_app(app)
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_CHECK_DEFAULT'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600

    # Add this near other app.config settings
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'temp'), exist_ok=True)

    @app.context_processor
    def inject_unread_messages_count():
        if current_user.is_authenticated:
            # Fetch the unread messages count for the current user
            unread_messages_count = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()
        else:
            unread_messages_count = 0  # Default to 0 if the user is not authenticated

        return dict(unread_messages_count=unread_messages_count)

    @app.template_filter('isinstance')
    def isinstance_filter(obj, cls):
        return isinstance(obj, cls)
    
    @app.teardown_appcontext
    def close_session(error):
        if hasattr(g, 'session'):
            g.session.close()

    @app.route('/health')
    def health():
        try:
            # Test pdfkit configuration with wkhtmltopdf
            config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
            pdfkit.from_string(
                '<h1>PDFKit is working!</h1>', 
                'test.pdf',
                configuration=config
            )
            return jsonify({
                "status": "healthy",
                "message": "pdfkit configuration successful"
            }), 200
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 500

    # Example route to generate PDF
    @app.route('/generate_pdf', methods=['POST'])
    def generate_pdf():
        html_content = '<h1>Welcome to the PDF Generation</h1>'
        pdfkit.from_string(html_content, 'welcome.pdf')
        return jsonify({"message": "PDF generated successfully", "filename": 'welcome.pdf'}), 200

    return app 
    

def update_expired_agreements():
    """Update agreements that have expired."""
    with app.app_context():
        try:
            # Query for expired agreements
            expired_agreements = RentalAgreement.query.filter_by(status='expired').all()
            for agreement in expired_agreements:
                # Perform your update logic here
                agreement.status = 'archived'  # Example update
                # Save changes to the database
                db.session.commit()
                logging.info(f"Updated agreement ID {agreement.id} to archived.")
        except Exception as e:
            logging.error(f"Error updating expired agreements: {e}")

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8000)