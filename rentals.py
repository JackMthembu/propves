from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from forms import GenerateLeaseForm
from models import RentalAgreement, Enquiry, Property
from extensions import db

rental_routes = Blueprint('rental_routes', __name__)

@rental_routes.route('/generate_rental_agreement/<int:enquiry_id>', methods=['GET', 'POST'])
@login_required
def generate_rental_agreement(enquiry_id):
    # Fetch the enquiry associated with the given enquiry_id
    enquiry = Enquiry.query.get_or_404(enquiry_id)
    property = enquiry.listing.property  # Assuming the enquiry has a relationship to the listing and property
    listing = enquiry.listing  # Get the listing from the enquiry

    form = GenerateLeaseForm()
    
    if form.validate_on_submit():
        try:
            # Create the RentalAgreement object
            rental_agreement = RentalAgreement(
                property_id=form.property_id.data,
                listing_id=listing.id,  # Use the listing ID
                tenant_id=form.tenant_id.data,
                owner_id=form.owner_id.data,
                sponsor_id=form.sponsor_id.data,
                company_id=form.company_id.data,
                date_start=form.date_start.data,
                date_end=form.date_end.data,
                monthly_rental=form.monthly_rental.data,
                deposit=form.deposit.data,
                admin_fee=form.admin_fee.data,
                daily_compounding=form.daily_compounding.data,
                water_sewer=form.water_sewer.data,
                electricity=form.electricity.data,
                gas=form.gas.data,
                waste_management=form.waste_management.data,
                internet=form.internet.data,
                additional_terms=form.additional_terms.data,
                status='draft'  # Set initial status
            )

            # Commit to the database
            db.session.add(rental_agreement)
            db.session.commit()
            flash('Rental agreement created successfully!', 'success')

            # Redirect to a confirmation page or the listing page
            return redirect(url_for('listing_routes.scheduled_enquiries'))

        except Exception as e:
            db.session.rollback()  # Rollback on error
            flash('An error occurred while creating the rental agreement: ' + str(e), 'danger')

    # Render the form for generating the rental agreement
    return render_template('rental/rental_agreement.html', form=form, enquiry=enquiry, property=property, listing=listing, agreement=None)
