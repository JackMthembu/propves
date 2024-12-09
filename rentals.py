from datetime import datetime, timedelta
from flask import Blueprint, current_app, make_response, render_template, request, redirect, url_for, flash, abort
from flask_mail import Mail, Message
from weasyprint import HTML
from extensions import db
from models import RentalAgreement, Property, Listing, User
from flask_login import current_user, login_required

mail = Mail()    

# mail = Mail(app)
def rental_routes(app):
    mail.init_app(app)

rental_routes = Blueprint('rental_routes', __name__)

@rental_routes.route('/create_agreement/<int:listing_id>', methods=['GET', 'POST'])
@login_required
def create_agreement(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    property = listing.property

    if property.owner_id != current_user.owner_id and current_user.manager_id is None:
        abort(403)

    if request.method == 'POST':
        # Get rental agreement data from the form
        deposit = request.form.get('deposit')
        monthly_rental = request.form.get('monthly_rental')
        date_start_str = request.form.get('date_start')
        date_end_str = request.form.get('date_end')
        tenant_id = request.form.get('tenant_id')
        vat_inclusion = request.form.get('vat_inclusion') == 'on'
        water = request.form.get('water') == 'on'
        electricity = request.form.get('electricity') == 'on'
        daily_compounding = float(request.form.get('daily_compounding', 0))

        # Basic validation
        if not all([deposit, monthly_rental, date_start_str, date_end_str, tenant_id]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('rental_routes.create_agreement', listing_id=listing_id))

        try:
            date_start = datetime.strptime(date_start_str, '%Y-%m-%d').date()
            date_end = datetime.strptime(date_end_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('rental_routes.create_agreement', listing_id=listing_id))

        # Get tenant and owner user IDs
        tenant_id = request.form.get('tenant_id')
        owner_id = property.owner_id

        # Create a new rental agreement
        agreement = RentalAgreement(
            deposit=deposit,
            monthly_rental=monthly_rental,
            date_start=date_start,
            date_end=date_end,
            property_id=property.id,
            tenant_id=tenant_id,
            owner_id=owner_id,
            manager_id=property.manager_id if property.manager_id else None,
            validity_end=datetime.utcnow() + timedelta(days=2),
            vat_inclusion=vat_inclusion,
            water=water,
            electricity=electricity,
            daily_compounding=daily_compounding,
            status='pending'
        )
        db.session.add(agreement)
        db.session.commit()

        send_lease_ready_email(tenant_id, agreement)

        # Generate lease and convert to PDF
        html = render_template('lease_template.html', agreement=agreement, property=property)
        response = make_response(HTML(string=html).write_pdf())
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'attachment', filename='lease_agreement.pdf')

        flash('Rental agreement created successfully!', 'success')
        return response

    return render_template('create_agreement.html', listing=listing, property=property)


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