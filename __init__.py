from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.from_object('config.Config')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth_routes.login'
    login_manager.login_message_category = 'info'
    
    # Register template filters
    @app.template_filter('format_currency')
    def format_currency(value):
        if value is None:
            return '$0.00'
        return f'${value:,.2f}'
    
    @app.template_filter('currency')
    def currency_filter(value):
        try:
            return f"{float(value):,.2f}"
        except (ValueError, TypeError):
            return "0.00"
    
    # Register blueprints
    from app import main_routes
    from auth import auth_routes
    from transaction import transaction_routes
    
    app.register_blueprint(main_routes)
    app.register_blueprint(auth_routes, url_prefix='/auth')
    app.register_blueprint(transaction_routes, url_prefix='/transactions')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app 