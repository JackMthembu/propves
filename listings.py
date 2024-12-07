from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, jsonify
from flask_login import login_required, current_user
from models import Property, Owner, Listing, RentalAgreement
from extensions import db
from forms import ListingForm
from datetime import datetime

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
            db.session.commit()
        elif listing.status is True:
            if latest_agreement and latest_agreement.status == 'pending':
                listing_status = 'Pending'
            else:
                listing_status = 'Listed'
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
    listing = Listing.query.get_or_404(listing_id)
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
