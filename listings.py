from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, jsonify
from flask_login import login_required, current_user
from models import Enquiry, Property, Owner, Listing, RentalAgreement
from extensions import db
from forms import GenerateLeaseForm, ListingForm
from datetime import date, datetime, timedelta

listing_routes = Blueprint('listing_routes', __name__)

@listing_routes.route('/listing/create_listing/<int:property_id>', methods=['GET', 'POST'])
@login_required
def create_listing(property_id):
    property = Property.query.get_or_404(property_id)
    form = ListingForm()

    if request.method == 'GET':
        return render_template('listing/create_listing.html', property=property, form=form)

    if form.validate_on_submit():
        try:
            new_listing = Listing(
                property_id=property_id,
                deposit=form.deposit.data,
                admin_fee=form.admin_fee.data,
                listing_type=form.listing_type.data,
                monthly_rental=form.monthly_rental.data,
                available_start_date=form.available_start_date.data,
                available_end_date=form.available_end_date.data,
                viewing_availibility_dates=form.viewing_availibility_dates.data,
                status=1,
                date_created=datetime.utcnow()
            )
            db.session.add(new_listing)
            db.session.commit()
            return jsonify({"message": "Listing created successfully!"}), 201

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating listing: {str(e)}")
            return jsonify({"error": "An error occurred while creating the listing."}), 500

@listing_routes.route('/listing/toggle_listing_status/<int:listing_id>', methods=['POST'])
@login_required
def toggle_listing_status(listing_id):
    try:
        listing = Listing.query.get_or_404(listing_id)
        property = listing.property
        current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()

        if not current_user_owner or property.owner_id != current_user_owner.id:
            abort(403)

        latest_agreement = RentalAgreement.query.filter_by(property_id=property.id).order_by(RentalAgreement.date_created.desc()).first()

        if latest_agreement and latest_agreement.status == 'accepted':
            listing.status = False
            property.status = 'occupied'
            db.session.commit()
        elif listing.status is True:
            if latest_agreement and latest_agreement.status == 'pending':
                listing_status = 'Pending'
            else:
                listing_status = 'Listed'
                property.status = 'listed'
                db.session.commit()
        else:
            listing_status = 'Unlisted'

        return redirect(url_for('listing_routes.property_list'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling listing status: {str(e)}")
        flash('Error updating listing status.', 'danger')
        return redirect(url_for('listing_routes.property_list'))

@listing_routes.route('/listing/edit_listing/<int:listing_id>', methods=['GET', 'POST'])
@login_required
def edit_listing(listing_id):
    listing = Listing.query.get(listing_id)
    if listing is None:
        return redirect(url_for('some_error_page'))

    property = listing.property
    form = ListingForm(obj=listing)

    if form.validate_on_submit():
        try:
            listing.deposit = form.deposit.data
            listing.admin_fee = form.admin_fee.data
            listing.listing_type = form.listing_type.data
            listing.monthly_rental = form.monthly_rental.data
            listing.available_start_date = form.available_start_date.data
            listing.available_end_date = form.available_end_date.data
            listing.viewing_availibility_dates = form.viewing_availibility_dates.data
            
            db.session.commit()
            flash('Listing updated successfully!', 'success')
            return redirect(url_for('property_routes.manage_property', property_id=property.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating listing: {str(e)}")
            flash('Error updating listing.', 'danger')

    return render_template('listing/edit_listing.html', listing=listing, property=property, form=form)

@listing_routes.route('/listing/scheduled_enquiries', methods=['GET', 'POST'])
@login_required
def scheduled_enquiries():
    # Fetch enquiries for the current user
    enquiries = Enquiry.query.filter(
        ((Enquiry.outcomes == 'scheduled') | (Enquiry.outcomes == 'agreement_generated')) &
        (Enquiry.owner.has(user_id=current_user.id)) 
    ).all()

    # Check and update outcomes for enquiries that are scheduled
    for enquiry in enquiries:
        if enquiry.outcomes == 'scheduled':
            # Check if 24 hours have passed since the scheduled date
            if datetime.utcnow() > enquiry.scheduled_date + timedelta(hours=24):
                enquiry.outcomes = 'rejected'  # Update outcome to 'rejected'
                db.session.add(enquiry)  # Add the updated enquiry to the session

    # Commit the changes to the database
    db.session.commit()

    # Optional filtering parameters
    scheduled_date = request.args.get('scheduled_date')
    listing_id = request.args.get('listing_id')
    tenant_id = request.args.get('tenant_id')

    # Apply additional filters if provided
    if scheduled_date:
        enquiries = [e for e in enquiries if e.scheduled_date == scheduled_date]
    if listing_id:
        enquiries = [e for e in enquiries if e.listing_id == listing_id]
        listing = Listing.query.get(listing_id)
    else:
        listing = None

    # Initialize the form with default values
    form = GenerateLeaseForm()
    
    # If enquiries exist, try to populate form with relevant data
    if enquiries:
        first_enquiry = enquiries[0]
        if first_enquiry.listing:
            form.monthly_rental.data = first_enquiry.listing.monthly_rental
            form.deposit.data = first_enquiry.listing.deposit
            form.date_start.data = date.today()
            form.date_end.data = date.today() + timedelta(days=365)

    enquiry = enquiries[0] if enquiries else None

    return render_template(
        'listing/scheduled_enquiries.html', 
        enquiries=enquiries, 
        listing=listing, 
        form=form, 
        enquiry=enquiry
    )

@listing_routes.route('/toggle_enquiry_outcome', methods=['POST'])
@login_required
def toggle_enquiry_outcome():
    enquiry_id = request.form.get('enquiry_id')
    # Assuming you have a function to get the enquiry by ID
    enquiry = get_enquiry_by_id(enquiry_id)  # Replace with your actual function

    if enquiry:
        enquiry.outcomes = 'Rejected'  # Set the outcome to 'Rejected'
        # Save the changes to the database
        save_enquiry(enquiry)  # Replace with your actual save function
        flash('Enquiry status updated to Rejected.', 'success')
    else:
        flash('Enquiry not found.', 'error')

    return redirect(url_for('listing_routes.scheduled_enquiries'))  # Redirect back to the scheduled enquiries page

@listing_routes.route('/toggle_enquiry_reschedule', methods=['POST'])
@login_required
def toggle_enquiry_reschedule():
    enquiry_id = request.form.get('enquiry_id')
    # Assuming you have a function to get the enquiry by ID
    enquiry = get_enquiry_by_id(enquiry_id)  # Replace with your actual function

    if enquiry:
        enquiry.outcomes = 'Rescheduled'  # Set the outcome to 'Rescheduled'
        # Save the changes to the database
        save_enquiry(enquiry)  # Replace with your actual save function
        flash('Enquiry status updated to Rescheduled.', 'success')
    else:
        flash('Enquiry not found.', 'error')

    return redirect(url_for('listing_routes.scheduled_enquiries'))

def save_enquiry(enquiry):
    db.session.add(enquiry)
    db.session.commit()

def get_enquiry_by_id(enquiry_id):
    return Enquiry.query.get(enquiry_id)
