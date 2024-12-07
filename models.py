import uuid
from flask import current_app
from flask_login import UserMixin, current_user
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import UUID, Boolean, Column, DateTime, ForeignKey, Integer, String, func
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
import json
from cachetools import TTLCache, cached
from sqlalchemy.types import JSON, TypeDecorator
from decimal import Decimal

db.metadata.clear()

class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string."""
    
    impl = db.Text  # Use Text as the underlying type for SQL Server
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    name = db.Column(db.String(50), nullable=True)
    lastname = db.Column(db.String(50), nullable=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    role = db.Column(db.String(20), nullable=True, default='user')
    password_hash = db.Column('password_hash', db.String(255), nullable=False)
    verification = db.Column(db.String(20), nullable=False, default='unverified')
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    account_locked = db.Column(db.Boolean, nullable=False, default=False)
    birthday = db.Column(db.Date, nullable=True) 
    gender = db.Column(db.String(10), nullable=True) 
    profile_picture = db.Column(db.String(150), nullable=True)
    phone_number = db.Column(db.String(15), nullable=True)
    employment = db.Column(db.String(100), nullable=True)
    employer = db.Column(db.String(100), nullable=True)
    monthly_income = db.Column(db.Numeric(10,2), nullable=True)
    next_of_keen_contacts = db.Column(db.String(150), nullable=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'))
    country_id = db.Column(db.String(3), db.ForeignKey('country.id'), nullable=True)
    currency_id = db.Column(db.String(3), db.ForeignKey('currency.id'), nullable=True)

    # Relationships
    country = db.relationship('Country', backref='users')
    rental_agreements = db.relationship('RentalAgreementUser', back_populates='user')
    owner = db.relationship('Owner', back_populates='user', uselist=False)
    managers = db.relationship('Manager', back_populates='user')
    subscription = db.relationship('Subscription', back_populates='user', uselist=False)
    currency = db.relationship('Currency', foreign_keys=[currency_id])

    # User cache with 5-minute TTL
    _cache = TTLCache(maxsize=100, ttl=300)

    # Password property and methods
    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute.')
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    

    # Token generation for email verification
    def generate_verification_token(self, secret_key):
        s = URLSafeTimedSerializer(secret_key)
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_verification_token(token, secret_key):
        s = URLSafeTimedSerializer(secret_key)
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['user_id'])
    
    def generate_reset_token(self, secret_key, expiration=3600): 
        s = URLSafeTimedSerializer(secret_key)
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')
    
    @staticmethod
    def verify_reset_token(token, secret_key):
        s = URLSafeTimedSerializer(secret_key)
        try:
            data = s.loads(token, salt='password-reset-salt', max_age=3600)  
        except Exception as e:
            print(f'Token verification error: {e}') 
            return None
        return User.query.get(data['user_id'])
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return not self.account_locked

    @property
    def is_anonymous(self):
        return False

    @classmethod
    @cached(cache=_cache)
    def get_by_id(cls, user_id):
        return cls.query.get(user_id)

    @classmethod
    def clear_cache(cls, user_id):
        if user_id in cls._cache:
            del cls._cache[user_id]

    def get_currency_symbol(self):
        """Get the currency symbol for this user"""
        if self.currency_id and self.currency:
            return self.currency.symbol
        return '$'  # Default fallback symbol

<<<<<<< HEAD
=======

class Calendar(db.Model):
    __tablename__ = 'calendar'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    date_start = db.Column(db.Date, nullable=False)
    date_end = db.Column(db.Date, nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # e.g., 'available', 'booked', 'maintenance'
    notes = db.Column(db.Text)
    
    # Relationship
    property = db.relationship('Property', back_populates='calendar')

    def __repr__(self):
        return f'<Calendar {self.property_id} - {self.date}>'


>>>>>>> origin/main
class Listing(db.Model):
    __tablename__ = 'listing'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
<<<<<<< HEAD
    deposit = db.Column(db.Numeric, nullable=False)
    admin_fee = db.Column(db.Numeric, nullable=False)
    listing_type = db.Column(db.String, nullable=False)
    monthly_rental = db.Column(db.Numeric, nullable=False)
    available_start_date = db.Column(db.Date, nullable=False)
    available_end_date = db.Column(db.Date, nullable=True)
    viewing_availibility_dates = db.Column(db.String(2000), nullable=True)  # Increase length if needed
    status = db.Column(db.Integer, nullable=False)
=======
    deposit = db.Column(db.Numeric(10, 2))
    admin_fee = db.Column(db.Numeric(10, 2))
    listing_type = db.Column(db.String(20), nullable=False) # 'student accommodation', 'room rental', 'shorty-term rental', 'family rental'
    monthly_rental = db.Column(db.Numeric(10, 2), nullable=False)
    available_start_date = db.Column(db.Date, nullable=False)
    available_end_date = db.Column(db.Date)
    status = db.Column(db.Boolean, default=True)  # True = active, False = inactive
>>>>>>> origin/main
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    property = db.relationship('Property', back_populates='listings')
    rental_agreements = db.relationship('RentalAgreement', back_populates='listing')

    def __repr__(self):
        return f"<Listing {self.id} for Property {self.property_id}>"

class Budget(db.Model):
    __tablename__ = 'budget'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    budget_type = db.Column(db.String(20), nullable=False) # renovation, maintainance, development
    budget_description = db.Column(db.String(200), nullable=True)
    budget_amount = db.Column(db.Numeric(10, 2), nullable=False)
    actual_amount = db.Column(db.Numeric(10, 2), nullable=False)
    execution_date = db.Column(db.Date, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    property = db.relationship('Property', back_populates='budget', foreign_keys=[property_id])
    
    def get_currency_symbol(self):
        """Get the currency symbol from the property owner's user currency"""
        if self.property and self.property.property_owner and self.property.property_owner.user:
            return self.property.property_owner.user.get_currency_symbol()
        return '$'  # Default fallback symbol

    def __repr__(self):
        return f"<Budget {self.id} for Property {self.property_id}>"

class Photo(db.Model):
    __tablename__ = 'photo'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    is_thumbnail = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    property = db.relationship('Property', back_populates='photos')

    def __repr__(self):
        return f"<Photo {self.id} for Property {self.property_id}>"

class Owner(db.Model):
    __tablename__ = 'owner'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='owner')
    properties = db.relationship('Property', back_populates='property_owner')
    managers = db.relationship('Manager', back_populates='owner')

<<<<<<< HEAD
=======
    @classmethod
    def get_or_create(cls, user_id):
        owner = cls.query.filter_by(user_id=user_id).first()
        if not owner:
            owner = cls(user_id=user_id)
            db.session.add(owner)
            db.session.commit()
        return owner

>>>>>>> origin/main
    def __repr__(self):
        return f'<Owner {self.id} user_id={self.user_id}>'

class Manager(db.Model):
    __tablename__ = 'manager'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='managers')
    owner = db.relationship('Owner', back_populates='managers')

class Tenant(db.Model):
    __tablename__ = 'tenant'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref='tenant', lazy=True)

class RentalAgreement(db.Model):
    __tablename__ = 'rental_agreement'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    
    # Dates
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_start = db.Column(db.Date, nullable=False)
    date_end = db.Column(db.Date, nullable=False)
    validity_end = db.Column(db.DATE, nullable=True)
    
    # Financial details
    deposit = db.Column(db.Numeric(10, 2), nullable=True)
    monthly_rental = db.Column(db.Numeric(10, 2), nullable=True)
    daily_compounding = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Inclusions
    vat_inclusion = db.Column(db.Boolean, default=False)
    water = db.Column(db.Boolean, default=False)
    electricity = db.Column(db.Boolean, default=False)
    
    # Relationships
    rental_users = db.relationship('RentalAgreementUser', back_populates='rental_agreement')
    property = db.relationship('Property', back_populates='rental_agreements')
    listing = db.relationship('Listing', back_populates='rental_agreements')
    rental_updates = db.relationship('RentalUpdates', back_populates='rental_agreement')

    def __repr__(self):
        return f"<RentalAgreement {self.id} for Property {self.property_id}>"

class RentalAgreementUser(db.Model):
    __tablename__ = 'rental_agreement_user'

    id = db.Column(db.Integer, primary_key=True)
    rental_agreement_id = db.Column(db.Integer, db.ForeignKey('rental_agreement.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # tenant, guarantor, agent, etc.
    
    # Relationships
    rental_agreement = db.relationship('RentalAgreement', back_populates='rental_users')
    user = db.relationship('User', back_populates='rental_agreements')

    def __repr__(self):
        return f"<RentalAgreementUser {self.user_id} ({self.role})>"
    
class RentalUpdates(db.Model):
    __tablename__ = 'rental_updates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rental_agreement_id = db.Column(db.Integer, db.ForeignKey('rental_agreement.id'), nullable=False)  
    date_update = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updates = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True) 

    rental_agreement = db.relationship('RentalAgreement', back_populates='rental_updates')

class Subscription(db.Model):
    __tablename__ = 'subscription'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    level = db.Column(db.String(20), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)

    # Relationships
    updates = db.relationship('SubscriptionUpdates', back_populates='subscription')
    user = db.relationship('User', back_populates='subscription', lazy=True)

class SubscriptionUpdates(db.Model):
    __tablename__ = 'subscription_updates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date_update = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True) 
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships - simplified
    subscription = db.relationship('Subscription', back_populates='updates')
    user = db.relationship('User', backref='subscription_updates')

class Transaction(db.Model):
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    transaction_date = db.Column(db.Date, nullable=False)
    processed_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    reference_number = db.Column(db.String(50), nullable=True)

    main_category = db.Column(db.String(50), nullable=False)  # Assets, Liabilities, Income, etc.
    sub_category = db.Column(db.String(50), nullable=True)   # Current Assets, Fixed Assets, etc.
    account = db.Column(db.String(50), nullable=False)        # Specific account

    # Document tracking
    document = db.Column(db.String(255), nullable=True)
    document_type = db.Column(db.String(10))
    extracted_data = db.Column(JSONEncodedDict, nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    
    # Relationships
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=True)
    
    # Status tracking
    is_verified = db.Column(db.Boolean, default=False)
    is_reconciled = db.Column(db.Boolean, default=False)
    is_portfolio = db.Column(db.Boolean, default=False)

<<<<<<< HEAD
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'processed_date': self.processed_date.isoformat() if self.processed_date else None,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'amount': float(self.amount) if self.amount else None,
            'description': self.description,
            'reference_number': self.reference_number,
            'main_category': self.main_category,
            'sub_category': self.sub_category,
            'account': self.account,
            'document': self.document,
            'document_type': self.document_type,
            'extracted_data': self.extracted_data,
            'confidence_score': self.confidence_score,
            'property_id': self.property_id,
            'owner_id': self.owner_id,
            'is_verified': self.is_verified,
            'is_reconciled': self.is_reconciled,
            'is_portfolio': self.is_portfolio
        }
=======

>>>>>>> origin/main

class Records(db.Model):
    __tablename__ = 'records'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Transaction details
    transaction_date = db.Column(db.Date, nullable=False)
    processed_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Amount handling (split into debit and credit)
    debit_amount = db.Column(db.Numeric(10, 2), nullable=True)
    credit_amount = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Classification fields
    main_category = db.Column(db.String(50), nullable=False)  # Assets, Liabilities, Income, etc.
    sub_category = db.Column(db.String(50), nullable=True)   # Current Assets, Fixed Assets, etc.
    account = db.Column(db.String(50), nullable=False)        # Specific account
    
    # Transaction details
    description = db.Column(db.String(200), nullable=True)
    reference_number = db.Column(db.String(50), nullable=True)  # For matching/reconciliation
    
    # Document tracking
    document = db.Column(db.String(255), nullable=True)
    document_type = db.Column(db.String(10))
    extracted_data = db.Column(JSONEncodedDict, nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    
    # Relationships
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=True)
    
    # Status tracking
    is_verified = db.Column(db.Boolean, default=False)
    is_reconciled = db.Column(db.Boolean, default=False)
    is_portfolio = db.Column(db.Boolean, default=False)
    
    @property
    def net_amount(self):
        """Calculate net amount (positive for debit, negative for credit)"""
        debit = Decimal(str(self.debit_amount or 0))
        credit = Decimal(str(self.credit_amount or 0))
        return debit - credit
    
    def __repr__(self):
        return f'<Transaction {self.id}: {self.main_category}/{self.sub_category}/{self.account}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'processed_date': self.processed_date.isoformat() if self.processed_date else None,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'debit_amount': float(self.debit_amount) if self.debit_amount else None,
            'credit_amount': float(self.credit_amount) if self.credit_amount else None,
            'main_category': self.main_category,
            'sub_category': self.sub_category,
            'account': self.account,
            'description': self.description,
            'reference_number': self.reference_number,
            'document': self.document,
            'document_type': self.document_type,
            'extracted_data': self.extracted_data,
            'confidence_score': self.confidence_score,
            'property_id': self.property_id,
            'owner_id': self.owner_id,
            'is_verified': self.is_verified,
            'is_reconciled': self.is_reconciled,
            'is_portfolio': self.is_portfolio
        }
    
class Country(db.Model):
    __tablename__ = 'country'

    id = db.Column(db.String(2), primary_key=True)  
    country = db.Column(db.String(100), nullable=False)
    currency_id = db.Column(db.String(3), db.ForeignKey('currency.id'), nullable=False)
    numeric_code = db.Column(db.String(3), nullable=False)

    states = db.relationship("State", back_populates="country", cascade="all, delete-orphan")
    currency = db.relationship('Currency', backref='countries')

    def __repr__(self):
        return f"<Country(id={self.id}, country={self.country})>"

class State(db.Model):
    __tablename__ = 'state'

    id = db.Column(db.String(3), primary_key=True)
    state = db.Column(db.String(50), nullable=False)  
    country_id = db.Column(db.String(2), db.ForeignKey('country.id'))

    country = db.relationship("Country", back_populates="states")

    def __repr__(self):
        return f"<State(id={self.id}, state={self.state}, country_id={self.country_id})>"

class Currency(db.Model):
    __tablename__ = 'currency'
    id = db.Column(db.String(3), primary_key=True)
    currency = db.Column(db.String(50), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f"<Currency(id={self.id}, currency={self.currency}, symbol={self.symbol})>"

class WishlistListing(db.Model):
    __tablename__ = 'wishlist_listing'
    
    wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlist.id'), primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), primary_key=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

class Wishlist(db.Model):
    __tablename__ = 'wishlist'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Remove the ARRAY field entirely
    listings = db.relationship('WishlistItem', backref='wishlist', lazy=True)

class WishlistItem(db.Model):
    __tablename__ = 'wishlist_items'
    
    id = db.Column(db.Integer, primary_key=True)
    wishlist_id = db.Column(db.Integer, db.ForeignKey('wishlist.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)

class Property(db.Model):
    __tablename__ = 'property'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Basic Property Details
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    sqm = db.Column(db.Numeric(10, 2), nullable=False)
    bedroom = db.Column(db.Integer, nullable=False)
    bathroom = db.Column(db.Integer, nullable=False)
    garage = db.Column(db.Integer, nullable=False)
    kitchen = db.Column(db.Integer, nullable=False)

    # Property Features
    swimming_pool = db.Column(db.Boolean, default=False)
    garden = db.Column(db.Boolean, default=False)
    air_conditioning = db.Column(db.Boolean, default=False)
    heating = db.Column(db.Boolean, default=False)
    gym = db.Column(db.Boolean, default=False)
    laundry = db.Column(db.Boolean, default=False)
    fireplace = db.Column(db.Boolean, default=False)
    balcony = db.Column(db.Boolean, default=False)
    pet_friendly = db.Column(db.Boolean, default=False)
    bbq_area = db.Column(db.Boolean, default=False)
    jacuzzi = db.Column(db.Boolean, default=False)
    tennis_court = db.Column(db.Boolean, default=False)

    # Property Address
    street_address = db.Column(db.String(255))
    building = db.Column(db.String(255))
    door_number = db.Column(db.String(20))
    suburb = db.Column(db.String(100))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

<<<<<<< HEAD
    #Lising
    status = db.Column(db.String(20), default=False) #unlisted #listed #occupied 


=======
>>>>>>> origin/main
    # Foreign Keys
    state_id = db.Column(db.String(3), db.ForeignKey('state.id'), nullable=True)
    country_id = db.Column(db.String(2), db.ForeignKey('country.id'), nullable=True)
    currency_id = db.Column(db.String(3), db.ForeignKey('currency.id'), nullable=True)
    
    # Relationships
    state = db.relationship('State', backref='properties')
    country = db.relationship('Country', backref='properties')
    currency = db.relationship('Currency', backref='properties')
    property_owner = db.relationship('Owner', back_populates='properties')
    rental_agreements = db.relationship('RentalAgreement', back_populates='property')
<<<<<<< HEAD
=======
    calendar = db.relationship('Calendar', back_populates='property', lazy='dynamic')
>>>>>>> origin/main
    photos = db.relationship('Photo', 
                           back_populates='property',
                           cascade="all, delete-orphan")
    listings = db.relationship('Listing', back_populates='property')
    budget = db.relationship('Budget', 
                           back_populates='property',
                           uselist=False,  # This makes it a one-to-one relationship
                           cascade="all, delete-orphan",
                           foreign_keys=[Budget.property_id])

    def __repr__(self):
        return f'<Property {self.id} owner_id={self.owner_id}>'

    @property
    def thumbnail(self):
        """Get the thumbnail photo for this property"""
        return (Photo.query.filter_by(property_id=self.id, is_thumbnail=True).first() 
                or (self.photos[0] if self.photos else None))

    @property
    def photo_count(self):
        """Get the number of photos for this property"""
        return Photo.query.filter_by(property_id=self.id).count()

    def get_currency_symbol(self):
        """Get the currency symbol for this property"""
        if self.currency_id and self.currency:
            return self.currency.symbol
        return '$'  # Default fallback symbol

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'owner_id': self.owner_id,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'description': self.description,
            'type': self.type,
        }

<<<<<<< HEAD
    @classmethod
    def autocomplete_search(cls, query, limit=10):
        """
        Search for properties by title, description, or address
        Returns properties that match the search query
        """
        search = f"%{query}%"
        return cls.query.filter(
            db.or_(
                cls.title.ilike(search),
                cls.description.ilike(search),
                cls.street_address.ilike(search),
                cls.city.ilike(search),
                cls.suburb.ilike(search)
            )
        ).limit(limit).all()

=======
>>>>>>> origin/main
class City(db.Model):
    __tablename__ = 'city'

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<City(id={self.id}, city={self.city})>"

class MonthlyExpenses(db.Model):
    __tablename__ = 'monthly_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    month = db.Column(db.DateTime, nullable=False)
    bill_type = db.Column(db.String(50))
    
    # Expense fields
    hoa_fees = db.Column(db.Numeric(10, 2), default=0)
    maintenance = db.Column(db.Numeric(10, 2), default=0)
    staff_cost = db.Column(db.Numeric(10, 2), default=0)
    management_fee = db.Column(db.Numeric(10, 2), default=0)
    reserve_fund = db.Column(db.Numeric(10, 2), default=0)
    special_assessments = db.Column(db.Numeric(10, 2), default=0)
    amenities = db.Column(db.Numeric(10, 2), default=0)
    other_expenses = db.Column(db.Numeric(10, 2), default=0)
    insurance = db.Column(db.Numeric(10, 2), default=0)
    property_taxes = db.Column(db.Numeric(10, 2), default=0)
    electricity = db.Column(db.Numeric(10, 2), default=0)
    gas = db.Column(db.Numeric(10, 2), default=0)
    water_sewer = db.Column(db.Numeric(10, 2), default=0)
    miscellaneous_cost = db.Column(db.Numeric(10, 2), default=0)
    other_city_charges = db.Column(db.Numeric(10, 2), default=0)
    
    # Relationships
<<<<<<< HEAD
    property = db.relationship('Property', backref='monthly_expenses')

class Enquiry(db.Model):
    __tablename__ = 'enquiry'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    outcomes = db.Column(db.String(50), default='scheduled')  #scheduled, #rejected #accepted

    # Relationships
    listing = db.relationship('Listing', backref='enquiries')
    user = db.relationship('User', backref='enquiries')
    owner = db.relationship('Owner', backref='enquiries')

    def __repr__(self):
        return f"<Enquiry {self.id} for Listing {self.listing_id}>"
=======
    property = db.relationship('Property', backref='monthly_expenses')
>>>>>>> origin/main
