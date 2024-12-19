from datetime import datetime, timedelta
from flask import Blueprint, current_app, make_response, render_template, request, redirect, url_for, flash, abort
from flask_mail import Mail, Message
from weasyprint import HTML
from extensions import db
from forms import GenerateLeaseForm
from models import Enquiry, RentalAgreement, Property, Listing, Tenant, User
from flask_login import current_user, login_required

mail = Mail()    

# mail = Mail(app)
def rental_routes(app):
    mail.init_app(app)

rental_routes = Blueprint('rental_routes', __name__)

@rental_routes.route('/create_agreement/<int:listing_id>', methods=['POST'])
@login_required
def create_agreement(listing_id):
    current_app.logger.debug(f"create_agreement route hit with listing_id: {listing_id}")
    
    form = GenerateLeaseForm()
    if form.validate_on_submit():
        try:
            current_app.logger.debug(f"Received data: {request.form}")
            current_app.logger.debug(f"Creating agreement for listing_id: {listing_id}")
            
            listing = Listing.query.get_or_404(listing_id)
            property = listing.property
            
            # Check if enquiry exists
            enquiry = Enquiry.query.filter_by(listing_id=listing_id).first()
            if not enquiry:
                current_app.logger.error(f"No enquiry found for listing {listing_id}.")
                flash('No associated enquiry found for this listing.', 'error')
                return redirect(url_for('listing_routes.scheduled_enquiries'))
            
            # Verify tenant
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

            # Instantiate the form with listing and tenant_id
            form = GenerateLeaseForm(listing=listing, tenant_id=tenant.id)

            # Authorization check
            if property.owner.user_id != current_user.id and current_user.manager_id is None:
                current_app.logger.warning(f"Unauthorized access attempt by user {current_user.id}")
                abort(403)

            # Form validation
            if form.validate_on_submit():
                agreement = RentalAgreement(
                    property_id=form.property_id.data,
                    listing_id=listing.id,
                    tenant_id=tenant.id,
                    owner_id=property.owner_id,
                    sponsor_id=tenant.sponsor_id,
                    deposit=form.deposit.data,
                    monthly_rental=form.monthly_rental.data,
                    admin_fee=form.admin_fee.data,
                    date_start=form.date_start.data,
                    date_end=form.date_end.data,
                    validity_end=datetime.utcnow() + timedelta(days=2),
                    waste_management=form.waste_management.data,
                    water_sewer=form.water_sewer.data,
                    electricity=form.electricity.data,
                    gas=form.gas.data,
                    internet=form.internet.data,
                    daily_compounding=form.daily_compounding.data,
                    additional_terms=form.additional_terms.data,
                    status='pending'
                )
                
                current_app.logger.debug(f"Agreement data before commit: {agreement.__dict__}")
                
                try:
                    db.session.add(agreement)
                    current_app.logger.debug("Attempting to commit the new agreement.")
                    db.session.commit()
                    current_app.logger.debug("Commit successful.")

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

                except Exception as commit_error:
                    db.session.rollback()  # Rollback on error
                    current_app.logger.error(f"Error during transaction: {str(commit_error)}")
                    flash('An error occurred while processing your request.', 'error')
                    return redirect(url_for('listing_routes.scheduled_enquiries'))

            # If form validation fails
            current_app.logger.warning(f"Form validation failed: {form.errors}")
            flash('Please fill in all required fields.', 'danger')
            return render_template('rental/rental_agreement.html', 
                                   listing=listing, 
                                   property=property, 
                                   form=form, 
                                   total_payable=total_payable)

        except Exception as e:
            current_app.logger.error(f"Error in create_agreement: {str(e)}")
            flash('An error occurred while processing your request.', 'error')
            return redirect(url_for('listing_routes.scheduled_enquiries'))
    else:
        current_app.logger.warning(f"Form validation failed: {form.errors}")
        flash('Please fill in all required fields.', 'danger')

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

    Please review and accept the agreement within 24 hours at:
    {agreement_url}

    If you do not accept the agreement within 24 hours, it will be automatically rejected.

    Sincerely,
    The Rental Team
    """

    mail.send(msg)

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

    # Log the fetched listing for debugging
    if listing is None:
        current_app.logger.warning(f"No listing found for property_id: {agreement.property_id}")

    # Pass the agreement, property, and listing to the template
    return render_template('rental/rental_agreement.html',
                           agreement=agreement,
                           property=property,
                           listing=listing)  # Ensure listing is passed here