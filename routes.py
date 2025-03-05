from ast import main
import os
from flask import Blueprint, abort, current_app, flash, redirect, render_template, url_for, request
from flask_login import current_user, login_required
from sqlalchemy import func
# from investment_analyses import oer_analysis
from models import MaintainanceReport, Property, Listing, RentalAgreement, Transaction, User, db, Message, Owner, BankingDetails
from datetime import datetime, timedelta, date
from sqlalchemy.orm import joinedload

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    current_app.logger.info("Index route accessed")
    # Get the filter type from the query parameters, default to 'past_year'
    filter_type = request.args.get('filter', 'past_year')
    # Logic to calculate date ranges based on the filter type
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
    elif filter_type == 'past_year':
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
    else:
        # Default to past year if filter type is not recognized
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

    active_maintainance = MaintainanceReport.query.filter(
        MaintainanceReport.reported_date >= start_date,
        MaintainanceReport.reported_date <= end_date,
        MaintainanceReport.status == 0,
        MaintainanceReport.property_id.in_(
            db.session.query(Property.id).filter(Property.owner.has(user_id=current_user.id))
        )  # Limit to current user's properties
    ).count()

    total_income = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.main_category == 'Revenue',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date,
        Transaction.is_reconciled == True,
        Transaction.owner.has(user_id=current_user.id)  
    ).scalar() or 0  

    total_operating_expenses = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.sub_category == 'Cost of Sales',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date,
        Transaction.is_reconciled == True,
        Transaction.owner.has(user_id=current_user.id) 
    ).scalar() or 0

    terminated_rental_agreements = db.session.query(RentalAgreement).filter(
        RentalAgreement.status == 'no_renewal',
        RentalAgreement.date_end >= start_date,
        RentalAgreement.date_end < end_date,
        RentalAgreement.owner.has(user_id=current_user.id)
    ).count() or 0

    tenant_count = active_rental_agreements()
    formatted_income = '{:,.2f}'.format(total_income)
    formatted_operating_expenses = '{:,.2f}'.format(total_operating_expenses)
    user = User.query.options(joinedload(User.currency)).filter_by(id=current_user.id).first()
    
    # Fetch the latest rental agreement for the current user
    agreement = RentalAgreement.query.join(Owner).filter(Owner.user_id == current_user.id).order_by(RentalAgreement.date_created.desc()).first()

    # Fetch the unread messages count
    unread_messages_count = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()

    # Query to get pending agreements for the current user's owner
    pending_agreements = RentalAgreement.query.filter_by(status='active', owner_id=current_user.id).all()
    progress_data = []

    for agreement in pending_agreements:
        if agreement.date_start and agreement.date_end:
            # Ensure both dates are datetime objects
            date_start = datetime.combine(agreement.date_start, datetime.min.time()) if isinstance(agreement.date_start, date) else agreement.date_start
            date_end = datetime.combine(agreement.date_end, datetime.min.time()) if isinstance(agreement.date_end, date) else agreement.date_end
            
            total_duration = (date_end - date_start).days
            elapsed_time = (datetime.now() - date_start).days
            progress_percentage = 100 - (elapsed_time / total_duration) * 100 if total_duration > 0 else 0
            progress_data.append({
                'property_title': agreement.property.title,
                'progress_percentage': min(max(progress_percentage, 0), 100)  # Clamp between 0 and 100
            })

    # Call the OER analysis function to get the category
    oer_category = oer_analysis()  # Ensure this function returns the category

    # current_app.logger.info(f"Total Operating Expenses: {total_operating_expenses}, Total Income: {total_income}, Operating Expenses Ratio: {operating_expenses_ratio}")

    banking_details_count = BankingDetails.query.filter_by(user_id=current_user.id).count()

    return render_template('dashboard/index.html', user=user, total_income=formatted_income, total_operating_expenses=formatted_operating_expenses, filter=filter_type, terminated_rental_agreements=terminated_rental_agreements, tenant_count=tenant_count, active_maintainance=active_maintainance, agreement=agreement, offer_validity=agreement.offer_validity if agreement else None, unread_messages_count=unread_messages_count, progress_data=progress_data, oer_category=oer_category, banking_details_count=banking_details_count, current_user=current_user)

@main.route('/maintenance')
def maintenance():
    # Fetch all maintenance reports
    reports = MaintainanceReport.query.all()
    
    # Fetch the unread messages count
    unread_messages_count = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()

    return render_template('dashboard/maintenance.html', reports=reports, unread_messages_count=unread_messages_count)

@main.route('/properties')
@login_required
def properties():
    if property.owner_id != current_user.owner_id and current_user.manager_id is None:
        abort(403)         
        flash('You do not have any properties associated with your account.', 'danger')
        return redirect(url_for('route.dashboard'))  

    properties = Property.query.filter_by(owner_id=current_user.owner_id).all()
    return render_template('dashboard/properties.html', properties=properties)

@main.route('/tenants')
def tenants():
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Eagerly load the 'currency' relationship
    owner = Owner.query.options(joinedload(Owner.user).joinedload(User.currency)).filter_by(user_id=current_user.id).first()

    active_tenants = RentalAgreement.query \
        .filter_by(owner=owner, status='active') \
        .order_by(RentalAgreement.id) \
        .paginate(page=page, per_page=per_page, error_out=False)

    # Calculate lease life percentage for each tenant
    for tenant in active_tenants.items:
        time_diff = tenant.date_end - tenant.date_start
        time_passed = datetime.utcnow() - datetime.combine(tenant.date_start, datetime.min.time())
        tenant.lease_life_percent = 100 - round((time_passed / time_diff * 100), 1)

    return render_template('dashboard/tenants.html', active_tenants=active_tenants)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

# Ensure the directory exists using current_app
def ensure_upload_folder_exists():
    if not os.path.exists(current_app.config['UPLOAD_FOLDER_PROFILE']):
        os.makedirs(current_app.config['UPLOAD_FOLDER_PROFILE'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['png', 'jpg', 'jpeg']


def active_rental_agreements():
    return RentalAgreement.query.filter(
        RentalAgreement.status == 'active',
        RentalAgreement.owner.has(user_id=current_user.id)
    ).count()

def pending_rental_agreements():
    return RentalAgreement.query.filter(
        RentalAgreement.status == 'pending',
        RentalAgreement.owner.has(user_id=current_user.id)
    ).count()

def expired_rental_agreements():
    return RentalAgreement.query.filter(
        RentalAgreement.status == 'expired',
        RentalAgreement.owner.has(user_id=current_user.id)
    ).count()

def count_active_maintainance_reports():
    count = db.session.query(MaintainanceReport).filter(
        MaintainanceReport.status == 'reported',
        MaintainanceReport.property_id.in_(
            db.session.query(Property.id).filter(Property.owner.has(user_id=current_user.id))
        )  
    ).count()
    return count

def count_resolved_maintainance_reports():
    count = db.session.query(MaintainanceReport).filter(
        MaintainanceReport.status == 'resolved',
        MaintainanceReport.property_id.in_(
            db.session.query(Property.id).filter(Property.owner.has(user_id=current_user.id))
        )
    ).count()
    return count

def get_expenses_summary():
    # Query to sum amounts grouped by sub_category where main_category is 'Expenses'
    expenses_summary = db.session.query(
        Transaction.sub_category,
        func.sum(Transaction.amount).label('total_amount')
    ).filter(
        Transaction.main_category == 'Expenses',
        Transaction.is_reconciled == True,
        Transaction.owner.has(user_id=current_user.id)  
    ).group_by(
        Transaction.sub_category
    ).all()

    # Convert the results to a dictionary for easier access
    summary_dict = {sub_category: float(total_amount) for sub_category, total_amount in expenses_summary}

    return summary_dict


def oer_analysis():
    try:
        # Fetch total operating expenses and total income from the database
        total_operating_expenses = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.sub_category == 'Operating Expenses',
            Transaction.is_reconciled == True,  # Only include reconciled transactions
            Transaction.owner.has(user_id=current_user.id)  # Limit to current user's properties
        ).scalar() or 0  # Default to 0 if no expenses

        total_income = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.main_category == 'Revenue',
            Transaction.is_reconciled == True,  # Only include reconciled transactions
            Transaction.owner.has(user_id=current_user.id)  # Limit to current user's properties
        ).scalar() or 1  # Default to 1 to avoid division by zero

        # Calculate OER
        operating_expenses_ratio = (total_operating_expenses / total_income) * 100 if total_income > 0 else 0

        # Determine the OER category
        if operating_expenses_ratio == 0:
            oer_category = ''  
        elif operating_expenses_ratio <= 20:
            oer_category = 'Excellent'
        elif operating_expenses_ratio <= 45:
            oer_category = 'Good'
        elif operating_expenses_ratio <= 60:
            oer_category = 'Moderate'
        else:
            oer_category = 'Not Good'

        # Log the OER category
        current_app.logger.info(f"OER Category: {oer_category}")

        return oer_category  # Ensure this returns the category

    except Exception as e:
        current_app.logger.error(f"Error in OER analysis: {str(e)}")
        return 'Error'  # Return a default value or error message 