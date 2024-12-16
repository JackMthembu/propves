from datetime import datetime, timedelta
from flask import Blueprint, current_app, make_response, render_template, request, redirect, url_for, flash, abort
from flask_mail import Mail, Message
from weasyprint import HTML
from extensions import db
from forms import GenerateLeaseForm
from listings import get_enquiry_by_id
from models import Company, Enquiry, RentalAgreement, Property, Listing, Tenant, User
from flask_login import current_user, login_required

mail = Mail()    

# mail = Mail(app)
def rental_routes(app):
    mail.init_app(app)

rental_routes = Blueprint('rental_routes', __name__)

@rental_routes.route('/create_agreement/<int:listing_id>', methods=['POST'])
@login_required
def create_agreement(listing_id):
    try:
        # Debug logging
        current_app.logger.debug(f"Creating agreement for listing_id: {listing_id}")
        
        listing = Listing.query.get_or_404(listing_id)
        property = listing.property
        
        # Debug: Check if enquiry exists
        if not listing.enquiry_id:
            current_app.logger.error(f"No enquiry found for listing {listing_id}")
            flash('No associated enquiry found for this listing.', 'error')
            return redirect(url_for('listing_routes.scheduled_enquiries'))
        
        enquiry = Enquiry.query.get_or_404(listing.enquiry_id)
        
        # Debug: Verify tenant
        tenant = enquiry.tenant
        if not tenant:
            current_app.logger.error(f"No tenant found for enquiry {enquiry.id}")
            flash('No tenant associated with this enquiry.', 'error')
            return redirect(url_for('listing_routes.scheduled_enquiries'))

        # Calculate total_payable
        total_payable = (
            enquiry.listing.monthly_rental or 0 + 
            enquiry.listing.deposit or 0 + 
            enquiry.listing.admin_fee or 0
        )
        current_app.logger.debug(f"Total payable: {total_payable}")

        # Instantiate the form with the listing and tenant_id
        form = GenerateLeaseForm(listing=listing, tenant_id=tenant.id)

        # Authorization check
        if property.owner.user_id != current_user.id and current_user.manager_id is None:
            current_app.logger.warning(f"Unauthorized access attempt by user {current_user.id}")
            abort(403)

        # Form validation
        if form.validate_on_submit():
            # Create a new rental agreement
            agreement = RentalAgreement(
                deposit=form.deposit.data,
                monthly_rental=form.monthly_rental.data,
                admin_fee=form.admin_fee.data,

                date_start=form.date_start.data,
                date_end=form.date_end.data,
                owner_id=property.owner_id,
                tenant_id=tenant.id,
                sponsor_id=form.sponsor_id.data,
                listing_id=listing.id,
                offer_validity=datetime.utcnow() + timedelta(days=1),
                gas=form.gas.data,
                water=form.water.data,
                electricity=form.electricity.data,
                waste_management=form.waste_management.data,
                internet=form.internet.data,
                daily_compounding=form.daily_compounding.data,
                status='pending',
            )
            db.session.add(agreement)
            db.session.commit()

            # Send lease ready email
            send_lease_ready_email(tenant.id, agreement)

            # Generate lease PDF
            try:
                html = render_template('/rental/rental_agreement.html', 
                                       agreement=agreement, 
                                       property=property,
                                       total_payable=total_payable)
                response = make_response(HTML(string=html).write_pdf())
                response.headers.set('Content-Type', 'application/pdf')
                response.headers.set('Content-Disposition', 'attachment', filename='lease_agreement_'+str(agreement.id)+'.pdf')
                
                flash('Rental agreement created successfully!', 'success')
                return response

            except Exception as pdf_error:
                current_app.logger.error(f"PDF generation error: {str(pdf_error)}")
                flash('Error generating the lease agreement PDF.', 'error')
                return redirect(url_for('rental_routes.scheduled_enquiries', agreement_id=agreement.id))

        # If form validation fails
        current_app.logger.warning(f"Form validation failed: {form.errors}")
        flash('Please fill in all required fields.', 'danger')
        return render_template('listing/scheduled_enquiries.html', 
                               listing=listing, 
                               property=property, 
                               form=form, 
                               total_payable=total_payable)

    except Exception as e:
        current_app.logger.error(f"Unexpected error in create_agreement: {str(e)}")
        flash('An unexpected error occurred.', 'error')
        return redirect(url_for('listing_routes.scheduled_enquiries'))


def send_lease_ready_email(tenant_id, agreement):
    tenant = User.query.get(tenant_id)
    if not tenant:
        return  # Handle case where tenant is not found

    agreement_url = url_for('rental_routes.rental_agreement', 
                          agreement_id=agreement.id, 
                          _external=True)

    msg = Message(
        'Your Lease Agreement is Ready',
        sender='notifications@propves.com',
        recipients=[tenant.email]
    )
    msg.body = f"""
    Dear {tenant.first_name},

    Your lease agreement for property ID {agreement.property_id} is ready for your acceptance.

    Please review and accept the agreement within 48 hours at:
    {agreement_url}

    If you do not accept the agreement within 48 hours, it will be automatically rejected.

    Sincerely,
    The Rental Team
    """

    mail.send(msg)

def generate_lease(enquiry, listing):
    # Logic to generate lease and send email
    property = Property.query.get(listing.property_id)
    tenant = Tenant.query.get(enquiry.user_id)  # Assuming user_id is the tenant_id
    form = GenerateLeaseForm()

    # Create rental agreement
    agreement = RentalAgreement(
        property_id=property.id,
        listing_id=listing.id,
        tenant_id=tenant.id,
        owner_id=property.owner_id,
        deposit=request.form.get('deposit'),
        monthly_rental=request.form.get('monthly_rental'),
        date_start=request.form.get('date_start'),
        date_end=request.form.get('date_end'),
        validity_end=datetime.utcnow() + timedelta(days=2),
        vat_inclusion=request.form.get('vat_inclusion') == 'on',
        water=request.form.get('water') == 'on',
        electricity=request.form.get('electricity') == 'on',
        daily_compounding=float(request.form.get('daily_compounding', 0)),
        status='pending'
    )
    db.session.add(agreement)
    db.session.commit()

    send_lease_ready_email(tenant.id, agreement)

    # Update listing outcome
    listing.outcomes = 'Rental Agreement Sent'
    db.session.commit()

@rental_routes.route('/rental_agreement/<int:agreement_id>', methods=['GET', 'POST'])
@login_required
def rental_agreement(agreement_id):
    # Get the rental agreement
    agreement = RentalAgreement.query.get_or_404(agreement_id)
    
    # Check if user has permission (either tenant, owner, or manager)
    if not (current_user.id == agreement.tenant_id or 
            current_user.owner_id == agreement.owner_id or 
            current_user.manager_id == agreement.manager_id):
        abort(403)

    if request.method == 'POST':
        action = request.form.get('action')
        
        try:
            if action == 'accept':
                # Update agreement status
                agreement.status = 'accepted'
                
                # Get the property's latest listing and set it to inactive
                latest_listing = Listing.query.filter_by(
                    property_id=agreement.property_id
                ).order_by(Listing.date_created.desc()).first()
                
                if latest_listing:
                    latest_listing.status = False
                
                db.session.commit()
                flash('Rental agreement accepted successfully!', 'success')
                
            elif action == 'reject':
                # Update agreement status
                agreement.status = 'rejected'
                db.session.commit()
                flash('Rental agreement rejected.', 'info')
                
            elif action == 'cancel':
                # Only allow cancellation if agreement is pending
                if agreement.status == 'pending':
                    agreement.status = 'cancelled'
                    db.session.commit()
                    flash('Rental agreement cancelled.', 'info')
                else:
                    flash('Cannot cancel an agreement that is not pending.', 'error')
            
            return redirect(url_for('rental_routes.rental_agreement', agreement_id=agreement_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating rental agreement: {str(e)}")
            flash('Error updating rental agreement.', 'error')

    # Get the property and listing information
    property = Property.query.get(agreement.property_id)
    listing = Listing.query.filter_by(
        property_id=agreement.property_id
    ).order_by(Listing.date_created.desc()).first()
    
    return render_template('rental_agreement.html',
                         agreement=agreement,
                         property=property,
                         listing=listing)