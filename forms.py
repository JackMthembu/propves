import re
from flask import current_app
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, DecimalField, FloatField, HiddenField, MultipleFileField, SelectField, StringField, IntegerField, PasswordField, SubmitField, TextAreaField, ValidationError
from typing import Optional
from wtforms.validators import Optional, Email, EqualTo, DataRequired, NumberRange, Length
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms_sqlalchemy.fields import QuerySelectField
from models import Country, Currency, db
from datetime import datetime, date, timedelta

from app_constants import ACCOUNTS, MAIN_CATEGORIES, SUB_CATEGORIES

class SearchForm(FlaskForm):
    location = StringField('Location', validators=[Optional()], render_kw={"placeholder": "Where to?"})
    date_range = StringField('Dates', validators=[Optional()], render_kw={"placeholder": "Dates"})
    submit = SubmitField('Search')

class SignUpForm(FlaskForm):
    username = StringField('Username', validators=[Optional()])
    name = StringField('First Name', validators=[Optional()])
    lastname = StringField('Last Name', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email()])
    password = PasswordField('Password', validators=[Optional()])
    confirm_password = PasswordField('Confirm Password', validators=[Optional(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    login_field = StringField('Email or Username', validators=[Optional()])
    password = PasswordField('Password', validators=[Optional()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[Optional()])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Reset Password')

class ResendVerificationForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Resend Verification Email')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Send Password Reset Email')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[Optional()])
    new_password = PasswordField('New Password', validators=[Optional()])
    confirm_password = PasswordField('Confirm New Password', validators=[
        Optional(),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Change Password')


class ProfileForm(FlaskForm):
    # Form fields with validators
    email = StringField('Email', validators=[Optional(), Email()])
    phone_number = StringField('Contact Number', validators=[Optional()])
    next_of_keen_contacts = StringField('Next of Ken Contacts')
    birthday = DateField('Birthday', format='%Y-%m-%d', validators=[Optional()])
    gender = SelectField('Gender', choices=[
        ('', 'Select Gender'),  
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say')
    ], validators=[DataRequired(message="Please select a gender")])
    country = SelectField('Country', choices=[], validators=[Optional()])
    currency_id = StringField('Currency', render_kw={'readonly': True})
    submit = SubmitField('Update Profile')

    def __init__(self, formdata=None, *args, current_user=None, **kwargs):
        super(ProfileForm, self).__init__(formdata=formdata, *args, **kwargs)
        
        # Always load country choices, regardless of whether it's a GET or POST
        self.country.choices = [(c.id, c.country) for c in Country.query.order_by(Country.country).all()]
        
        # Only populate from current_user if this is not a form submission
        if current_user:
            user = db.session.merge(current_user)
            
            if not formdata:  # Only set initial values if not a form submission
                # Pre-populate form data
                self.email.data = user.email
                self.phone_number.data = user.phone_number
                self.next_of_keen_contacts.data = user.next_of_keen_contacts
                self.birthday.data = user.birthday
                self.gender.data = user.gender or ''
                
                if user.country_id:
                    self.country.data = user.country_id
                    currency = Currency.query.select_from(Country).join(Currency)\
                        .filter(Country.id == user.country_id).first()
                    if currency:
                        self.currency_id.data = currency.id
                    self.country.render_kw = {'disabled': True}
                
                # Set readonly/disabled fields based on existing data
                if user.birthday:
                    self.birthday.render_kw = {'readonly': True}
                if user.gender:
                    self.gender.render_kw = {'disabled': True}
                if user.phone_number:
                    self.phone_number.render_kw = {'readonly': True}

    def validate_country(self, field):
        if field.data:
            # Debug logging
            current_app.logger.debug(f"Validating country: {field.data}")
            current_app.logger.debug(f"Available choices: {dict(self.country.choices)}")
            
            # Check if the country exists in the database
            country = Country.query.get(field.data)
            if not country:
                raise ValidationError('Invalid country selection.')

    def validate_phone_number(self, field):
        if field.data:
            pattern = r"^\+?[1-9]\d{1,14}$"
            if not re.match(pattern, field.data):
                raise ValidationError('Invalid phone number. It must be in international format (e.g., +27123456789).')

class EmploymentProfile(FlaskForm):
    employment = StringField('Current Employment', validators=[Optional()])
    employer = StringField('Current Employer', validators=[Optional()])
    birthday = DateField('Birthday', format='%Y-%m-%d', validators=[Optional()])
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female')])
    country = SelectField('Country', choices=[], validators=[Optional()])
    currency_id = StringField('Currency', render_kw={'readonly': True}) 
    monthly_income = DecimalField('Monthly Income', validators=[Optional()])
    submit = SubmitField('Update Profile')

class ProfilePicForm(FlaskForm):
    profile_picture = FileField('Upload Profile Picture', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Upload Picture')

class CSRFOnlyForm(FlaskForm):
    pass

class SubscriptionForm(FlaskForm):
    subscription = SelectField('Subscription', choices=[('basic', 'Basic'), ('standard', 'Standard'), ('premium', 'Premium')])
    submit = SubmitField('Subscribe')

class PropertyDetailsForm(FlaskForm):
    title = StringField('Title', 
        validators=[DataRequired(), Length(min=3, max=100)])
    
    type = SelectField('Type',
        choices=[
            ('Apartment', 'Apartment'),
            ('Co-op', 'Co-op'),
            ('Condo', 'Condo'),
            ('Townhouse', 'Townhouse'),
            ('House', 'House'),
            ('Office', 'Office'),
            ('Retail', 'Retail'),
            ('industrial', 'Industrial'),
            ('Loft', 'Loft'),
            ('Mixed-use', 'Mixed-Use')
        ],
        validators=[DataRequired()])
    
    description = TextAreaField('Description',
        validators=[DataRequired(), Length(min=10, max=1000)])
    
    bedroom = IntegerField('Bedrooms', 
        validators=[Optional(), NumberRange(min=0, max=20)],
        default=0)
    
    bathroom = IntegerField('Bathrooms',
        validators=[Optional(), NumberRange(min=0, max=20)],
        default=0)
    
    kitchen = IntegerField('Kitchens',
        validators=[Optional(), NumberRange(min=0, max=20)],
        default=0)
    
    garage = IntegerField('Parking',
        validators=[Optional(), NumberRange(min=0, max=20)],
        default=0)
    
    sqm = DecimalField('Square Feet',
        validators=[Optional(), NumberRange(min=0)],
        default=0.0)
    
    submit = SubmitField('Save Details')
    
class FeatureForm(FlaskForm):
    swimming_pool = BooleanField('Swimming Pool')
    garden = BooleanField('Garden')
    air_conditioning = BooleanField('Air Conditioning')
    heating = BooleanField('Heating')
    gym = BooleanField('Gym')
    laundry = BooleanField('Laundry')
    fireplace = BooleanField('Fireplace')
    balcony = BooleanField('Balcony')
    pet_friendly = BooleanField('Pet Friendly')
    bbq_area = BooleanField('BBQ Area')
    jacuzzi = BooleanField('Jacuzzi')
    tennis_court = BooleanField('Tennis Court')
    submit = SubmitField('Update')


class AddressForm(FlaskForm):
    street_address = StringField('Street Address', render_kw={
        "autocomplete": "off",
        "role": "combobox",
        "aria-autocomplete": "list",
        "id": "street_address",
        "placeholder": "Start typing your address..."
    })
    
    building = StringField('Building', render_kw={
        "id": "building"
    })
    
    door_number = StringField('Door Number', render_kw={
        "id": "door_number"
    })

    suburb = StringField('Suburb/District', render_kw={
        "autocomplete": "off",
        "readonly": True,
        "id": "suburb"
    })
    city = StringField('City/Town', render_kw={
        "autocomplete": "off",
        "readonly": True,
        "id": "city"
    })
    state_id = StringField('State/Region/Province', render_kw={
        "autocomplete": "off",
        "readonly": True,
        "id": "state_id"
    })
    country_id = StringField('Country', render_kw={
        "autocomplete": "off",
        "readonly": True,
        "id": "country_id"
    })
    latitude = HiddenField('Latitude', render_kw={"id": "latitude"})
    longitude = HiddenField('Longitude', render_kw={"id": "longitude"})
    submit = SubmitField('Update')


class PhotoForm(FlaskForm):
    thumbnail = FileField('Thumbnail', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    photos = MultipleFileField('Additional Photos', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Upload Photos')


class MonthlyExpensesForm(FlaskForm):
    month = DateField('Date', 
                     validators=[DataRequired()],
                     format='%Y-%m-%d',  # HTML5 date format
                     default=datetime.today,  # Set default to today
                     render_kw={
                         "type": "date",
                         "class": "form-control"
                     })
    bill_type = SelectField('Bill Type', 
                          choices=[('Monthly', 'Monthly'), 
                                 ('Quarterly', 'Quarterly'),
                                 ('Annually', 'Annually')],
                          validators=[DataRequired()])
    
    # Add all expense fields with proper validation
    hoa_fees = DecimalField('Association Fees', places=2, default=0.00)
    maintenance = DecimalField('Maintenance', places=2, default=0.00)
    staff_cost = DecimalField('Staff Cost', places=2, default=0.00)
    management_fee = DecimalField('Management Fee', places=2, default=0.00)
    reserve_fund = DecimalField('Reserve Fund', places=2, default=0.00)
    special_assessments = DecimalField('Special Assessments', places=2, default=0.00)
    amenities = DecimalField('Amenities', places=2, default=0.00)
    other_expenses = DecimalField('Other Expenses', places=2, default=0.00)
    property_taxes = DecimalField('Property Taxes', places=2, default=.00)
    insurance = DecimalField('Insurance', places=2, default=0.00)
    
    electricity = DecimalField('Electricity', places=2, default=0.00)    
    gas = DecimalField('Gas', places=2, default=0.00)
    water_sewer = DecimalField('Water/Sewer', places=2, default=0.00)
    miscellaneous_cost = DecimalField('Miscellaneous Cost', places=2, default=0.00)
    other_city_charges = DecimalField('Other City Charges', places=2, default=0.00)

    # ... add other fields similarly
    
    # Document Upload
    document = FileField('Supporting Document', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Allowed file types: JPG, JPEG, PNG, PDF')
    ])
    
    submit = SubmitField('Save Expenses')



class FixedExpensesForm(FlaskForm):
    fixed_expense = StringField('Expense Name', validators=[Optional()])
    amount = DecimalField('Amount', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    document = FileField('Supporting Document', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Allowed file types: JPG, JPEG, PNG, PDF')
    ])
    submit = SubmitField('Add/Update Expense')


class ProfilePicForm(FlaskForm):
    profile_picture = FileField('Upload Profile Picture', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Upload Picture')

class CSRFOnlyForm(FlaskForm):
    pass

class SubscriptionUpdatesForm(FlaskForm):
    update = SelectField('Update', choices=[('cancel', 'Cancel'), ('downgrade', 'Downgrade'), ('upgrade', 'Upgrade')])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Add Update')

class ListingForm(FlaskForm):
    deposit = DecimalField('Deposit', validators=[DataRequired()])
    admin_fee = DecimalField('Admin Fee', validators=[Optional()], default=0.00)
    monthly_rental = DecimalField('Monthly Rental', validators=[DataRequired()])
    available_start_date = DateField('Available From', validators=[DataRequired()])
    available_end_date = DateField('Available Until', validators=[Optional()])
    viewing_availibility_dates = StringField('Viewing Availability Dates')
    listing_type = SelectField('Viewing Availability', 
                                     choices=[
                                         ('student_accommodation', 'Student Accommodation'),
                                         ('room', 'Room'),
                                         ('family_home', 'Family Home'),
                                         ('vaccaion_rental', 'Vaccation Rental')
                                     ],
                                     default='flexible',
                                     validators=[DataRequired()])
    submit = SubmitField('Create Listing')

    def validate_viewing_availibility_dates(form, field):
        # Regex to match the expected format
        pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2} - \d{2}:\d{2}(, \d{4}-\d{2}-\d{2} \d{2}:\d{2} - \d{2}:\d{2})*$'
        if not re.match(pattern, field.data):
            raise ValidationError('Invalid date format. Use YYYY-MM-DD HH:MM - HH:MM, YYYY-MM-DD HH:MM - HH:MM.')

class ExpensesOverviewForm(FlaskForm):
    start_date = DateField('Start Date', 
                          validators=[DataRequired()], 
                          format='%Y-%m-%d',
                          default=lambda: datetime.now().replace(day=1) - timedelta(days=365))
    end_date = DateField('End Date', 
                        validators=[DataRequired()], 
                        format='%Y-%m-%d',
                        default=lambda: datetime.now())
    property_id = SelectField('Property', 
                            coerce=int, 
                            validators=[Optional()],
                            default=0)

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError('End date must be after start date')

class ExpensesFilterForm(FlaskForm):
    month = DateField('Month', format='%Y-%m', validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])
    bill_type = SelectField('Bill Type', 
                          choices=[('Monthly', 'Monthly'), 
                                 ('Quarterly', 'Quarterly'),
                                 ('Annually', 'Annually')],
                          validators=[DataRequired()])

class ExpenseFilterForm(FlaskForm):
    """Form for filtering transaction expenses"""
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    property_id = SelectField('Property', coerce=int, validators=[Optional()])
    category = SelectField('Category', choices=[], validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(ExpenseFilterForm, self).__init__(*args, **kwargs)
        # Populate category choices from ACCOUNT_CLASSIFICATIONS
        self.category.choices = [('', 'All Categories')] + [
            (cat, cat) for cat in ACCOUNTS['Expenses']
        ]

def get_account_choices():
    """Helper function to get account choices organized by category"""
    choices = []
    for category, accounts in ACCOUNTS.items():
        group = (category, [(account, account) for account in accounts])
        choices.append(group)
    return choices

class AccountForm(FlaskForm):
    account = SelectField('Account', choices=get_account_choices())
    # ... rest of your form code ...

class TransactionForm(FlaskForm):
    transaction_date = DateField('Date', validators=[DataRequired()])
    property_id = SelectField('Property', coerce=int, validators=[DataRequired()])
    account = SelectField('Account', choices=[], validators=[DataRequired()])
    description = StringField('Description', validators=[Optional()])
    Aamount = DecimalField('Debit', places=2, validators=[Optional()])
    is_reconciled = BooleanField('Reconciled')
    submit = SubmitField('Submit')

class TransactionFilterForm(FlaskForm):
    """Form for filtering transactions"""
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    category = SelectField('Category', validators=[Optional()], 
        choices=[('', 'All')] + [(cat, cat) for cat in MAIN_CATEGORIES])
    account = SelectField('Account', validators=[Optional()],
        choices=[('', 'All')] + [
            (account, account)
            for category in ACCOUNTS.values()
            for account in category
        ])
    property_id = SelectField('Property', coerce=int, validators=[Optional()])

class BudgetForm(FlaskForm):
    property_id = SelectField('Property', coerce=int, validators=[DataRequired()])
    budget_type = SelectField('Budget Type', choices=[('renovation', 'Renovation'), ('maintenance', 'Maintenance'), ('development', 'Development'), ('other', 'Other')], validators=[DataRequired()])
    budget_description = StringField('Description', validators=[DataRequired()])
    budget_amount = DecimalField('Budget Amount', validators=[DataRequired(), NumberRange(min=0)])
    actual_amount = DecimalField('Actual Amount', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Submit')

    pass