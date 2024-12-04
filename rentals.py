from datetime import datetime, timedelta
from flask import Blueprint, app, make_response, render_template, request, redirect, url_for, flash, abort
from flask_mail import Mail, Message
from weasyprint import HTML
from extensions import db
from models import RentalAgreement, Calendar, Property, Listing, User
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
            daily_compounding=daily_compounding
        )
        db.session.add(agreement)
        

        # Update calendar status to 'pending offer'
        calendar_entries = Calendar.query.filter_by(property_id=property.id).all()
        for entry in calendar_entries:
            if entry.date_start <= date_start and entry.date_end >= date_end:
                entry.status = 'pending offer'

        db.session.commit()

        send_lease_ready_email(tenant_id, agreement.id)

        # Generate lease and convert to PDF
        html = render_template('lease_template.html', agreement=agreement, property=property)
        response = make_response(HTML(string=html).write_pdf())
        response.headers.set('Content-Type', 'application/pdf')
        response.headers.set('Content-Disposition', 'attachment', filename='lease_agreement.pdf')

        flash('Rental agreement created successfully!', 'success')
        return response

    return render_template('create_agreement.html', listing=listing, property=property)


def send_lease_ready_email(tenant_id, agreement_id):
    tenant = User.query.get(tenant_id)
    if not tenant:
        return  # Handle case where tenant is not found

    # Construct the email
    msg = Message(
        'Your Lease Agreement is Ready',
        sender='notifications@propves.com',
        recipients=[tenant.email]
    )
    msg.body = f"""
    Dear {tenant.first_name},

    Your lease agreement for property ID {agreement_id.property_id} is ready for your acceptance.

    Please review and accept the agreement within 48 hours.

    [Link to accept the agreement]

    If you do not accept the agreement within 48 hours, it will be automatically rejected.

    Sincerely,
    The Rental Team
    """

    # Send the email
    mail.send(msg)