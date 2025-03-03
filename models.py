from flask_login import UserMixin
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
import json
from cachetools import TTLCache, cached
from sqlalchemy.types import TypeDecorator
from decimal import Decimal
from sqlalchemy.orm import relationship

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
    name = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    role = db.Column(db.String(20), nullable=True, default='Landlord')
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
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)
    currency_id = db.Column(db.String(3), db.ForeignKey('currency.id'), nullable=True)
    id_number = db.Column(db.String(100), nullable=True, unique=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)

    # Address
    street_address = db.Column(db.String(255), nullable=True)
    building = db.Column(db.String(255), nullable=True)
    door_number = db.Column(db.String(20), nullable=True)
    suburb = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state_id = db.Column(db.String(3), db.ForeignKey('state.id'), nullable=True)
    country_id = db.Column(db.String(3), db.ForeignKey('country.id'), nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)

    # Setting
    system = db.Column(db.String(20), default='metric')

    # Relationships
    country = db.relationship('Country', backref='users')
    state = db.relationship('State', backref='users')
    owner = db.relationship('Owner', back_populates='user', uselist=False)
    # tenant = db.relationship('Tenant', back_populates='user', uselist=False)
    managers = db.relationship('Manager', back_populates='user')
    subscription = db.relationship('Subscription', back_populates='user', uselist=False)
    currency = db.relationship('Currency', foreign_keys=[currency_id])
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient')
    company = db.relationship('Company', back_populates='users')
    banking_details = db.relationship('BankingDetails', back_populates='user', uselist=False)
    maintainance_reports = db.relationship('MaintainanceReport', back_populates='user')
    maintainance_updates = db.relationship('MaintainanceUpdates', back_populates='user')

    # New relationship for wishlist
    wishlists = db.relationship('Wishlist', backref='user', lazy=True)

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

class Listing(db.Model):
    __tablename__ = 'listing'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    deposit = db.Column(db.Numeric, nullable=False)
    listing_type = db.Column(db.String, nullable=False)
    monthly_rental = db.Column(db.Numeric, nullable=False)
    available_start_date = db.Column(db.Date, nullable=False)
    available_end_date = db.Column(db.Date, nullable=True)
    viewing_availibility_dates = db.Column(db.String(2000), nullable=True)  # Increase length if needed
    status = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    admin_fee = db.Column(db.Numeric, nullable=False)

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
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    maintainance_report_id = db.Column(db.Integer, db.ForeignKey('maintainance_report.id'), nullable=True)
    file_path = db.Column(db.String, nullable=False)
    filename = db.Column(db.String, nullable=False)
    is_thumbnail = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    property = db.relationship('Property', back_populates='photos')
    maintainance_report = db.relationship('MaintainanceReport', back_populates='photos')

    def __repr__(self):
        return f"<Photo {self.id} for Property {self.property_id}>"

class Owner(db.Model):
    __tablename__ = 'owner'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', back_populates='owner')
    properties = db.relationship('Property', back_populates='owner')
    managers = db.relationship('Manager', back_populates='owner')
    rental_agreements = db.relationship('RentalAgreement', back_populates='owner')
    transactions = db.relationship('Transaction', back_populates='owner')
    enquiries = db.relationship('Enquiry', back_populates='owner')

    def __repr__(self):
        return f'<Owner {self.id} user_id={self.user_id}>'

class Company(db.Model):
    __tablename__ = 'company'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    company_registration_number = db.Column(db.String(100), nullable=False)
    tax_number =  db.Column(db.String(100), nullable=False)
    users = db.relationship('User', back_populates='company')

    rental_agreements = relationship('RentalAgreement', back_populates='company')


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
    sponsor_id = db.Column(db.Integer, db.ForeignKey('sponsor.id'), nullable=True)

    user = db.relationship('User', backref='tenant', lazy=True)
    rental_agreements = db.relationship('RentalAgreement', back_populates='tenant')
    enquiry_tenant = db.relationship('Enquiry', back_populates='tenant')
    
    # Define the relationship to Sponsor
    sponsor = db.relationship('Sponsor', back_populates='tenants', foreign_keys=[sponsor_id])

    # Relationships
    enquiries = db.relationship('Enquiry', back_populates='tenant')

class Sponsor(db.Model):
    __tablename__ = 'sponsor'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref='sponsor', lazy=True)
    rental_agreements = db.relationship('RentalAgreement', back_populates='sponsor')

    # Define the relationship to Tenant
    tenants = db.relationship('Tenant', back_populates='sponsor', foreign_keys=[Tenant.sponsor_id])

class RentalAgreement(db.Model):
    __tablename__ = 'rental_agreement'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey('enquiry.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False)
    
    # Dates
    date_created = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    date_start = db.Column(db.Date, nullable=True)
    date_end = db.Column(db.Date, nullable=True)
    offer_validity = db.Column(db.DateTime, nullable=True)
    term_months = db.Column(db.Integer, nullable=True)
    term_years = db.Column(db.Integer, nullable=True)

    # Financial details
    deposit = db.Column(db.Numeric(10, 2), nullable=True)
    monthly_rental = db.Column(db.Numeric(10, 2), nullable=True)
    daily_compounding = db.Column(db.Numeric(10, 2), default=0.0)
    admin_fee  = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Inclusions
    water_sewer = db.Column(db.Boolean, default=True)
    electricity = db.Column(db.Boolean, default=True)
    gas = db.Column(db.Boolean, default=True)
    waste_management = db.Column(db.Boolean, default=True)
    internet = db.Column(db.Boolean, default=True)

    # Pets and Sub-letting
    pets_allowed = db.Column(db.Boolean, default=False)  # Field to indicate if pets are allowed
    sub_letting_allowed = db.Column(db.Boolean, default=False)  # Field to indicate if sub-letting is allowed
    max_occupants = db.Column(db.Integer, nullable=True)
    nightly_guest_rate = db.Column(db.Numeric(10, 2), nullable=True)
    create_as_company = db.Column(db.Boolean, default=False) # if true, the lease will be created as a company lease    

    # Users
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('sponsor.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    
    additional_terms = db.Column(db.Text, nullable=True)

    # Company
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)

    # Relationships
    property = db.relationship('Property', back_populates='rental_agreements')
    listing = db.relationship('Listing', back_populates='rental_agreements')
    rental_updates = db.relationship('RentalUpdates', back_populates='rental_agreement')
    owner = db.relationship('Owner', back_populates='rental_agreements')
    tenant = db.relationship('Tenant', back_populates='rental_agreements')
    sponsor = db.relationship('Sponsor', back_populates='rental_agreements')
    company = db.relationship('Company', back_populates='rental_agreements')

    def __repr__(self):
        return f"<RentalAgreement {self.id} for Property {self.property_id}>"
  
class RentalUpdates(db.Model):
    __tablename__ = 'rental_updates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rental_agreement_id = db.Column(db.Integer, db.ForeignKey('rental_agreement.id'), nullable=False)  
    date_update = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updates = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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
    sub_category = db.Column(db.String(50), nullable=True)      # Current Assets, Fixed Assets, etc.
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
    is_property_tax = db.Column(db.Boolean, default=False)

    owner = relationship('Owner', back_populates='transactions') 

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

    id = db.Column(db.String(2), primary_key=True)
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
    zip_code = db.Column(db.Integer)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    #Lising
    status = db.Column(db.String(20), default='unlisted') #unlisted #listed #occupied 
    max_occupants = db.Column(db.Integer, nullable=False)

    # Foreign Keys
    state_id = db.Column(db.String(3), db.ForeignKey('state.id'), nullable=True)
    country_id = db.Column(db.String(2), db.ForeignKey('country.id'), nullable=True)
    currency_id = db.Column(db.String(3), db.ForeignKey('currency.id'), nullable=True)

    # Property Taxes
    tax_assessed_value = db.Column(db.Numeric(10, 2), nullable=True)
    tax_rate = db.Column(db.Float, nullable=True)  
    tax_year = db.Column(db.Integer, nullable=True)  
    tax_exemptions = db.Column(db.String(255), nullable=True)  
    rental_income_tax_rate = db.Column(db.Float, nullable=True) 

    
    # Relationships
    state = db.relationship('State', backref='properties')
    country = db.relationship('Country', backref='properties')
    currency = db.relationship('Currency', backref='properties')
    owner = db.relationship('Owner', back_populates='properties')
    rental_agreements = db.relationship('RentalAgreement', back_populates='property')
    photos = db.relationship('Photo', 
                           back_populates='property',
                           cascade="all, delete-orphan")
    listings = db.relationship('Listing', back_populates='property')
    budget = db.relationship('Budget', 
                           back_populates='property',
                           uselist=False, 
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
    
    def full_address(self):
        """Return the complete address of the property."""
        address_parts = [
            self.street_address,
            self.building,
            self.door_number,
            self.suburb,
            self.city,
            self.state.state if self.state else None,  
            self.country.country if self.country else None, 
            self.zip_code
        ]
        return ", ".join(filter(None, address_parts))  

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

class City(db.Model):
    __tablename__ = 'city'

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<City(id={self.id}, city={self.city})>"


class Enquiry(db.Model):
    __tablename__ = 'enquiry'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    outcomes = db.Column(db.String(50), default='scheduled')  #scheduled, #rejected #accepted

    # Relationships
    listing = db.relationship('Listing', backref='enquiries')
    tenant = db.relationship('Tenant', back_populates='enquiries')  
    owner = db.relationship('Owner', back_populates='enquiries')  

    def __repr__(self):
        return f"<Enquiry {self.id} for Listing {self.listing_id}>"

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.recipient_id}>'

class BankingDetails(db.Model):
    __tablename__ = 'banking_details'

    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(50), nullable=False)
    account_holder_name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(100), nullable=True)
    branch_code = db.Column(db.String(10), nullable=True)
    account_iban = db.Column(db.String(34), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bank_id = db.Column(db.Integer, db.ForeignKey('banks.id'), nullable=False)

    # New fields
    nickname = db.Column(db.String(100), nullable=True)
    is_primary = db.Column(db.Boolean, default=False)

    # Define the relationship with User
    user = db.relationship('User', back_populates='banking_details')
    bank = db.relationship('Banks', back_populates='banking_details')

    def __repr__(self):
        return f'<BankingDetails {self.id} for User {self.user_id}>'

    def set_primary(self):
        # Set this account as primary
        self.is_primary = True
        
        # Unset primary status for all other accounts of the same user
        BankingDetails.query.filter(
            BankingDetails.user_id == self.user_id,
            BankingDetails.id != self.id
        ).update({"is_primary": False})
        
        db.session.commit()

class Banks(db.Model):
    __tablename__ = 'banks'

    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(100), nullable=False)
    bank_code = db.Column(db.String(10), nullable=True)
    bank_swift_code = db.Column(db.String(12), nullable=True)
    country_id = db.Column(db.String(3), db.ForeignKey('country.id'), nullable=False)
    state_id = db.Column(db.String(3), db.ForeignKey('state.id'), nullable=True)
    
    banking_details = db.relationship('BankingDetails', back_populates='bank')
    country = db.relationship('Country', backref='banks')
    state = db.relationship('State', backref='banks')

    def __repr__(self):
        return f'<Banks {self.id} {self.bank_name}>'

class MaintainanceReport(db.Model):
    __tablename__ = 'maintainance_report'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    maintainance_type = db.Column(db.String(50), nullable=False)
    reported_date = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Report
    status = db.Column(db.Boolean, nullable=False, default=False)  # reported = False, resolved = True
    description = db.Column(db.Text, nullable=False)

    # Relationships
    photos = db.relationship('Photo', back_populates='maintainance_report')
    user = db.relationship('User', back_populates='maintainance_reports')
    updates = db.relationship('MaintainanceUpdates', back_populates='maintainance_report')

    def __repr__(self):
        return f'<MaintainanceReport {self.id} for Property {self.property_id}>'

class MaintainanceUpdates(db.Model):
    __tablename__ = 'maintainance_updates'

    id = db.Column(db.Integer, primary_key=True)
    maintainance_report_id = db.Column(db.Integer, db.ForeignKey('maintainance_report.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    update_description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)

    # Relationships
    maintainance_report = db.relationship('MaintainanceReport', back_populates='updates')
    user = db.relationship('User', back_populates='maintainance_updates')

class Notification(db.Model):
    __tablename__ = 'notification'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False) #warning, info, success, error
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Users
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('sponsor.id'), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('manager.id'), nullable=True)

    # Notifications for
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=True)
    maintenance_report_id = db.Column(db.Integer, db.ForeignKey('maintenance_report.id'), nullable=True)
    rental_agreement_id = db.Column(db.Integer, db.ForeignKey('rental_agreement.id'), nullable=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey('enquiry.id'), nullable=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)
    banking_details_id = db.Column(db.Integer, db.ForeignKey('banking_details.id'), nullable=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rental_agreement_id = db.Column(db.Integer, db.ForeignKey('rental_agreement.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    rental_agreement = db.relationship('RentalAgreement', backref='payments')

    def __repr__(self):
        return f'<Payment {self.id} - {self.amount} - {self.date}>'