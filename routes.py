from ast import main
import os
from flask import Blueprint, abort, current_app, flash, redirect, render_template, url_for, request
from flask_login import current_user, login_required
from models import MaintainanceReport, Property, Listing, RentalAgreement, Transaction, User, db
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def dashboard():
    # Get the filter type from the query parameters
    filter_type = request.args.get('filter', 'this_month')
    
    # Logic to count active maintenance reports based on the filter type
    if filter_type == 'today':
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    elif filter_type == 'this_month':
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(day=1, month=datetime.now().month + 1, hour=0, minute=0, second=0, microsecond=0) if datetime.now().month < 12 else datetime.now().replace(year=datetime.now().year + 1, month=1, day=1)
    elif filter_type == 'last_month':
        start_date = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
        end_date = datetime.now().replace(day=1)
    elif filter_type == 'this_year':
        start_date = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(month=1, day=1, year=datetime.now().year + 1)

    active_maintainance = MaintainanceReport.query.filter(
        MaintainanceReport.reported_date >= start_date,
        MaintainanceReport.reported_date <= end_date,
        MaintainanceReport.status == 0
    ).count()

    # Other counts and logic remain unchanged
    terminated_count = terminated_rental_agreements(filter_type)
    total_income = calculate_total_income_month() if filter_type == 'month' else calculate_total_income()
    tenant_count = active_rental_agreements()
    formatted_income = '{:,.2f}'.format(total_income)
    user = User.query.options(joinedload(User.currency)).filter_by(id=current_user.id).first()

    return render_template('dashboard.html', user=user, total_income=formatted_income, filter=filter_type, terminated_count=terminated_count, tenant_count=tenant_count, active_maintainance=active_maintainance)

@main.route('/pricing-rtl')
def pricing_rtl():
    return render_template('pricing-rtl.html')

@main.route('/pricing')
def pricing():
    return render_template('pricing.html')

@main.route('/maintenance')
def maintenance():
    return render_template('maintenance.html')

@main.route('/properties')
@login_required
def properties():
    if property.owner_id != current_user.owner_id and current_user.manager_id is None:
        abort(403)         
        flash('You do not have any properties associated with your account.', 'danger')
        return redirect(url_for('route.dashboard'))  

    properties = Property.query.filter_by(owner_id=current_user.owner_id).all()
    return render_template('properties.html', properties=properties)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

# Ensure the directory exists using current_app
def ensure_upload_folder_exists():
    if not os.path.exists(current_app.config['UPLOAD_FOLDER_PROFILE']):
        os.makedirs(current_app.config['UPLOAD_FOLDER_PROFILE'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['png', 'jpg', 'jpeg']

# Function to calculate total income for the current year
def calculate_total_income():
    # Define the start date for the current year
    start_of_year = datetime(datetime.utcnow().year, 1, 1)

    # Query to sum the amount of transactions categorized as 'Revenue'
    total_income = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.main_category == 'Revenue',
        Transaction.transaction_date >= start_of_year
    ).scalar() or 0  # Use 0 if there are no matching transactions

    return total_income

def calculate_total_income_month():
    # Define the start date for the current month
    start_of_month = datetime(datetime.utcnow().year, datetime.utcnow().month, 1)

    # Query to sum the amount of transactions categorized as 'Revenue'
    total_income = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.main_category == 'Revenue',
        Transaction.transaction_date >= start_of_month
    ).scalar() or 0  # Use 0 if there are no matching transactions

    return total_income

def active_rental_agreements():
    return RentalAgreement.query.filter_by(status='active').count()

def pending_rental_agreements():
    return RentalAgreement.query.filter_by(status='pending').count()

def expired_rental_agreements():
    return RentalAgreement.query.filter_by(status='expired').count()

def terminated_rental_agreements(filter_type='3_months'):
    if filter_type == 'this_month':
        start_date = datetime.now().replace(day=1)  # First day of the current month
        end_date = datetime.now().replace(day=1) + timedelta(days=31)  # First day of next month
    else:  # Default to '3_months'
        end_date = datetime.now()  # Current date
        start_date = end_date - timedelta(days=90)  # 3 months ago

    return RentalAgreement.query.filter(
        RentalAgreement.status == 'no_renewal',
        RentalAgreement.date_end >= start_date,
        RentalAgreement.date_end < end_date
    ).count()

def count_active_maintainance_reports():
    count = db.session.query(MaintainanceReport).filter(MaintainanceReport.status == 'reported').count()
    return count

def count_resolved_maintainance_reports():
    count = db.session.query(MaintainanceReport).filter(MaintainanceReport.status == 'resolved').count()
    return count