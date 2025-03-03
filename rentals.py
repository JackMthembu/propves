from flask import Blueprint, abort, current_app, render_template, redirect, send_file, url_for, flash, request, make_response
from flask_login import login_required, current_user
from forms import GenerateLeaseForm
from models import Listing, Message, RentalAgreement, Enquiry, Property, Owner, User, RentalUpdates
from extensions import db, mail
from datetime import datetime, timedelta
from flask_mail import Message
import pdfkit
import os
from PyPDF2 import PdfReader
import uuid

rental_routes = Blueprint('rental_routes', __name__)

@rental_routes.route('/generate_rental_agreement/<int:enquiry_id>', methods=['GET', 'POST'])
@login_required
def generate_rental_agreement(enquiry_id):

    enquiry = Enquiry.query.get_or_404(enquiry_id)
    property = enquiry.listing.property  
    listing = enquiry.listing
    sponsor_id = enquiry.tenant.sponsor_id 
    company_id = enquiry.owner.user.company_id
    deposit = enquiry.listing.deposit
    monthly_rental = enquiry.listing.monthly_rental
    admin_fee = enquiry.listing.admin_fee
    max_occupants = property.max_occupants

    form = GenerateLeaseForm()
    
    if form.validate_on_submit():
        try:
            # Log the form data for debugging
            current_app.logger.debug(f"Form data: {form.data}")

            # Update the enquiry outcome
            enquiry.outcomes = 'agreement_generated'  # Set the outcome to 'agreement_generated'

            # Calculate the term
            date_start = form.date_start.data
            date_end = form.date_end.data
            term_months = (date_end.year - date_start.year) * 12 + (date_end.month - date_start.month)
            term_years = term_months // 12
            term_months = term_months % 12
            submission_time = datetime.now()  # Capture the current time at submission
            offer_validity = submission_time + timedelta(hours=24)  # Set offer validity to 24 hours from submission

            rental_agreement = RentalAgreement(
                enquiry_id=form.enquiry_id.data,
                property_id=form.property_id.data,
                listing_id=listing.id,  
                tenant_id=form.tenant_id.data,
                owner_id=form.owner_id.data,
                sponsor_id=sponsor_id,
                company_id=company_id,
                date_start=date_start,
                date_end=date_end,
                monthly_rental=monthly_rental,
                deposit=deposit,
                admin_fee=admin_fee,
                max_occupants=max_occupants,
                nightly_guest_rate=form.nightly_guest_rate.data,
                daily_compounding=form.daily_compounding.data,
                water_sewer=form.water_sewer.data,
                electricity=form.electricity.data,
                gas=form.gas.data,
                waste_management=form.waste_management.data,
                internet=form.internet.data,
                additional_terms=form.additional_terms.data,
                pets_allowed=form.pets_allowed.data,
                sub_letting_allowed=form.sub_letting_allowed.data,
                status='draft',
                term_months=term_months,
                term_years=term_years,
                create_as_company=form.create_as_company.data,
                offer_validity=offer_validity
            )

            # Commit to the database
            db.session.add(rental_agreement)
            db.session.commit()

            # Update the enquiry in the database
            db.session.commit()  # Commit the changes to the enquiry

            # Commit the enquiry changes
            db.session.add(enquiry)  # Add the updated enquiry to the session
            db.session.commit()  # Commit the changes to the enquiry

            flash('Rental agreement created successfully!', 'success')

            # Redirect to the view of the created agreement
            return redirect(url_for('rental_routes.view_rental_agreement', enquiry=enquiry, property=property, listing=listing, user=current_user, rental_agreement_id=rental_agreement.id))

        except Exception as e:
            db.session.rollback()  # Rollback on error
            current_app.logger.error(f"Error creating rental agreement: {str(e)}")
            flash('An error occurred while creating the rental agreement: ' + str(e), 'danger')

    # Render the form for generating the rental agreement
    return render_template('listing/_create_agreement.html', form=form, enquiry=enquiry, property=property, listing=listing, user=current_user)

@rental_routes.route('/view_rental_agreement/<int:rental_agreement_id>', methods=['GET'])
@login_required
def view_rental_agreement(rental_agreement_id):
    rental_agreement = RentalAgreement.query.get_or_404(rental_agreement_id)

    # Set default values for term_years and term_months if None
    rental_agreement.term_years = rental_agreement.term_years if rental_agreement.term_years is not None else 0
    rental_agreement.term_months = rental_agreement.term_months if rental_agreement.term_months is not None else 0

    # Fetch the owner associated with the rental agreement
    owner = Owner.query.get(rental_agreement.owner_id)
    if owner is None:
        flash('Owner not found for this rental agreement.', 'danger')
        return redirect(url_for('some_safe_route'))  # Redirect to a safe route

    # Fetch the enquiry associated with the rental agreement
    enquiry = Enquiry.query.filter_by(id=rental_agreement.enquiry_id).first()
    if enquiry is None:
        flash('Enquiry not found for this rental agreement.', 'danger')
        return redirect(url_for('some_safe_route'))  # Redirect to a safe route

    # Fetch the apartment associated with the rental agreement
    apartment = Property.query.get(rental_agreement.property_id)
    if apartment is None:
        flash('Apartment not found for this rental agreement.', 'danger')
        return redirect(url_for('some_safe_route'))  # Redirect to a safe route

    return render_template('rental/rental_agreement.html',
                           agreement=rental_agreement,
                           owner=owner,
                           enquiry=enquiry,
                           apartment=apartment)


@rental_routes.route('/save_lease/<int:tenant_id>', methods=['POST'])
@login_required
def save_lease(tenant_id):
    # Fetch the rental agreement associated with the tenant
    agreement = RentalAgreement.query.filter_by(tenant_id=tenant_id).first()  # Adjust this line based on your model relationships

    if agreement:
        # Send the lease ready email
        send_lease(tenant_id, agreement)

        # Update the rental agreement status to 'pending'
        agreement.status = 'pending'
        
        # Create a new rental update entry
        rental_update = RentalUpdates(
            rental_agreement_id=agreement.id,
            user_id=current_user.id,
            updates='pending',
            description='Lease agreement sent to ' + agreement.tenant.user.email
        )
        
        # Add the rental update to the session
        db.session.add(rental_update)
        
        # Commit the changes to the database
        db.session.commit()

        flash('Lease ready email sent successfully!', 'success')
    else:
        flash('Error: Rental agreement not found.', 'danger')

    return redirect(url_for('rental_routes.view_rental_agreement_pdf', rental_agreement_id=agreement.id))

def send_lease(tenant_id, agreement):
    # Prepare email details
    subject = "Lease Agreement"
    sender_email = current_app.config['MAIL_DEFAULT_SENDER']
    recipient_email = agreement.tenant.user.email
    
    # Create the agreement URL for accepting the lease
    agreement_url = url_for('rental_routes.rental_agreement', agreement_id=agreement.id, _external=True)

    # Create the message
    msg = Message(subject=subject, sender=sender_email, recipients=[recipient_email])
    msg.body = f"""
    Dear {agreement.tenant.user.name},

    Your lease agreement for property {agreement.property.title} is ready for your acceptance.

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
    
        # Check and update outcomes for enquiries that are scheduled

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

    # Fetch the owner associated with the rental agreement
    owner = Owner.query.get(agreement.owner_id)

    # Fetch the apartment associated with the rental agreement
    apartment = Property.query.get(agreement.property_id)

    # Check if apartment is None
    if apartment is None:
        current_app.logger.warning(f"No apartment found for property_id: {agreement.property_id}")

    # Pass the agreement, property, listing, owner, and apartment to the template
    return render_template('rental/rental_agreement.html',
                           agreement=agreement,
                           property=property,
                           listing=listing,
                           owner=owner,
                           apartment=apartment)

@rental_routes.route('/rental_agreement/<int:agreement_id>/pdf', methods=['GET'])
@login_required
def view_rental_agreement_pdf(agreement_id):
    agreement = RentalAgreement.query.get_or_404(agreement_id)
    
    # Fetch the owner associated with the rental agreement
    owner = Owner.query.get(agreement.owner_id)
    if owner is None:
        flash('Owner not found for this rental agreement.', 'danger')
        return redirect(url_for('some_safe_route'))  # Redirect to a safe route

    # Fetch the apartment associated with the rental agreement
    apartment = Property.query.get(agreement.property_id)
    if apartment is None:
        flash('Apartment not found for this rental agreement.', 'danger')
        return redirect(url_for('some_safe_route'))  # Redirect to a safe route

    # Render the HTML template to a string
    rendered = render_template('rental/rental_agreement_pdf.html', agreement=agreement, owner=owner, apartment=apartment)

    # Create a PDF from the rendered HTML
    pdf_file_path = f'temp_rental_agreement_{agreement_id}.pdf'
    pdfkit.from_string(rendered, pdf_file_path)

    # Return the PDF file for preview
    response = send_file(pdf_file_path, as_attachment=False, mimetype='application/pdf')

    # Clean up the temporary file after sending
    os.remove(pdf_file_path)

    return response

@rental_routes.route('/rental_agreement/<int:agreement_id>/download', methods=['GET'])
@login_required
def download_rental_agreement(agreement_id):
    agreement = RentalAgreement.query.get_or_404(agreement_id)
    
    # Fetch the owner associated with the rental agreement
    owner = Owner.query.get(agreement.owner_id)
    if owner is None:
        flash('Owner not found for this rental agreement.', 'danger')
        return redirect(url_for('some_safe_route'))  # Redirect to a safe route

    # Fetch the apartment associated with the rental agreement
    apartment = Property.query.get(agreement.property_id)
    if apartment is None:
        flash('Apartment not found for this rental agreement.', 'danger')
        return redirect(url_for('some_safe_route'))  # Redirect to a safe route

    # Render the HTML template to a string
    rendered = render_template('rental/rental_agreement_pdf.html', agreement=agreement, owner=owner, apartment=apartment)

    # Create a PDF from the rendered HTML
    pdf = pdfkit.from_string(rendered, False)

    # Create a response with the PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=rental_agreement_{agreement_id}.pdf'

    return response

@rental_routes.route('/send_rental_agreement/<int:agreement_id>', methods=['POST'])
@login_required
def send_rental_agreement(agreement_id):
    agreement = RentalAgreement.query.get_or_404(agreement_id)
    tenant_email = agreement.tenant.user.email  # Assuming you have the tenant's email

    # Generate a unique token for signing
    unique_token = str(uuid.uuid4())
    agreement.signing_token = unique_token  # Store the token in the database
    db.session.commit()

    # Create the agreement URL for signing
    agreement_url = url_for('rental_routes.sign_agreement', token=unique_token, _external=True)

    # Prepare email details
    subject = "Lease Agreement - Please Sign"
    sender_email = current_app.config['MAIL_DEFAULT_SENDER']
    
    # Create the message
    msg = Message(subject=subject, sender=sender_email, recipients=[tenant_email])
    msg.body = f"""
    Dear {agreement.tenant.user.name},

    Your lease agreement for property {agreement.property.title} is ready for your signature.

    Please sign the agreement at the following link:
    {agreement_url}

    Sincerely,
    The Rental Team
    """

    mail.send(msg)
    flash('Rental agreement sent to tenant for signing!', 'success')
    return redirect(url_for('rental_routes.view_rental_agreement', agreement_id=agreement_id))

@rental_routes.route('/sign_agreement/<token>', methods=['GET', 'POST'])
def sign_agreement(token):
    agreement = RentalAgreement.query.filter_by(signing_token=token).first()
    if not agreement:
        flash('Invalid signing link.', 'danger')
        return redirect(url_for('some_safe_route'))

    if request.method == 'POST':
        # Capture the signature (you can use a library like Signature Pad)
        signature = request.form.get('signature')  # Assuming you have a form field for the signature
        agreement.tenant_signature = signature  # Save the tenant's signature
        agreement.status = 'signed_by_tenant'  # Update the status
        db.session.commit()

        # Notify the owner to sign
        # (You can implement similar logic to send an email to the owner)

        flash('Agreement signed by tenant. Waiting for owner to sign.', 'success')
        return redirect(url_for('rental_routes.view_rental_agreement', agreement_id=agreement.id))

    return render_template('rental/sign_agreement.html', agreement=agreement)

@rental_routes.route('/finalize_agreement/<int:agreement_id>', methods=['POST'])
@login_required
def finalize_agreement(agreement_id):
    agreement = RentalAgreement.query.get_or_404(agreement_id)

    if agreement.status == 'signed_by_owner':
        # Generate the final signed PDF
        rendered = render_template('rental/rental_agreement_pdf.html', agreement=agreement)
        final_pdf = pdfkit.from_string(rendered, False)

        # Save the final signed PDF
        final_pdf_path = f'final_signed_agreement_{agreement_id}.pdf'
        with open(final_pdf_path, 'wb') as f:
            f.write(final_pdf)

        # Update the agreement status
        agreement.status = 'finalized'
        db.session.commit()

        flash('Agreement finalized and saved successfully!', 'success')
        return send_file(final_pdf_path, as_attachment=True)

    flash('Agreement is not ready for finalization.', 'danger')
    return redirect(url_for('rental_routes.view_rental_agreement', agreement_id=agreement_id))

@rental_routes.route('/manage_agreements', methods=['GET'])
@login_required
def manage_agreements():

    agreements = RentalAgreement.query.filter(
        (RentalAgreement.status == 'pending') |
        (Enquiry.outcomes == 'agreement_generated') |
        (Enquiry.outcomes == 'active')
    ).filter(
        RentalAgreement.owner.has(user_id=current_user.id)
    ).all()

    for agreement in agreements:
        if agreement.status == 'pending':
            if datetime.utcnow() > agreement.date_created + timedelta(hours=24):
                agreement.status = 'expired' 
                db.session.add(agreement) 

    db.session.commit()

    return render_template('rental/manage_agreements.html', agreements=agreements)

def generate_pdf():
    html_content = '<h1>Rental Agreement</h1><p>This is your rental agreement.</p>'
    pdfkit.from_string(html_content, 'rental_agreement.pdf')

