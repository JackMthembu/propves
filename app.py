from cachetools import TTLCache
from dotenv import load_dotenv
from extensions import db, mail, login_manager, migrate
from flask import Flask, config, jsonify
import os
from config import Config
import logging
from models import User
from routes import main
from auth import auth_routes
from flask_login import LoginManager, UserMixin
from datetime import timedelta
from flask_wtf.csrf import CSRFProtect
from messaging import message_routes
from profiles import profile_routes
from property import property_routes
from listings import listing_routes
from rentals import rental_routes 
from transaction import transaction_routes 
from accounting import accounting_routes

app = Flask(__name__)  
app.secret_key = os.getenv('SECRET_KEY') 

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

request_cache = TTLCache(maxsize=100, ttl=5)  

logging.basicConfig(level=logging.INFO)

# Initialize the login manager
login_manager = LoginManager()
 # Add other fields as necessary
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Replace User with your user model

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, template_folder='templates')

    load_dotenv()

    app.config.from_object(Config)
    app.config.update(
        CELERY_BROKER_URL=os.getenv('CELERY_BROKER_URL'),
        CELERY_RESULT_BACKEND=os.getenv('CELERY_RESULT_BACKEND'),
        API_NINJA_API_KEY=os.getenv('API_NINJA_API_KEY'),
        GOOGLE_MAPS_API_KEY=os.getenv('GOOGLE_MAPS_API_KEY'),
        SECRET_KEY=os.getenv('SECRET_KEY'),
        PERMANENT_SESSION_LIFETIME=timedelta(days=31)
    )

    print("Loaded configuration:", app.config)  
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)   
    csrf.init_app(app)
    app.register_blueprint(main)
    app.register_blueprint(auth_routes, url_prefix='/auth')
    app.register_blueprint(message_routes)
    app.register_blueprint(profile_routes)
    app.register_blueprint(property_routes)
    app.register_blueprint(listing_routes)
    app.register_blueprint(rental_routes)
    app.register_blueprint(transaction_routes)
    app.register_blueprint(accounting_routes)

    return app  

if __name__ == '__main__':
    app = create_app()  
    app.run(host='0.0.0.0', port=8000)