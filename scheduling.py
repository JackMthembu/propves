from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, abort
from extensions import db
from models import Calendar, Property
from flask_login import current_user, login_required

calendar_routes = Blueprint('calendar_routes', __name__)

@calendar_routes.route('/manage_calendar/<int:property_id>', methods=['GET', 'POST'])
@login_required
def manage_property_calendar(property_id):
    """Manage calendar for a specific property."""
    property = Property.query.get_or_404(property_id)

    # Check if the user is the owner or an authorized manager
    if property.owner_id != current_user.owner_id and current_user.manager_id is None:
        abort(403)

    if request.method == 'POST':
        # Get calendar data from the form
        calendar_api = request.form.get('calendar_api')
        date_start_str = request.form.get('date_start')
        date_end_str = request.form.get('date_end')
        status = request.form.get('status')

        # Basic validation
        if not all([calendar_api, date_start_str, date_end_str, status]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('calendar_routes.manage_property_calendar', property_id=property_id))

        try:
            date_start = datetime.strptime(date_start_str, '%Y-%m-%dT%H:%M')
            date_end = datetime.strptime(date_end_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return redirect(url_for('calendar_routes.manage_property_calendar', property_id=property_id))

        # Create a new calendar entry
        calendar_entry = Calendar(
            calendar_api=calendar_api,
            date_start=date_start,
            date_end=date_end,
            status=status,
            property_id=property_id,
            user_id=current_user.id
        )
        db.session.add(calendar_entry)
        db.session.commit()

        flash('Calendar entry added successfully!', 'success')
        return redirect(url_for('calendar_routes.manage_property_calendar', property_id=property_id))

    # Get existing calendar entries for the property
    calendar_entries = Calendar.query.filter_by(property_id=property_id).all()

    return render_template('manage_property_calendar.html', property=property, calendar_entries=calendar_entries)


@calendar_routes.route('/manage_calendar')
@login_required
def manage_all_calendars():
    """Manage combined calendar for all properties."""
    # Get all properties owned by the user
    properties = Property.query.filter_by(owner_id=current_user.owner_id).all()

    # Get calendar entries for all properties
    calendar_entries = []
    for property in properties:
        entries = Calendar.query.filter_by(property_id=property.id).all()
        for entry in entries:
            entry.property_title = property.title  # Add property title to the entry
        calendar_entries.extend(entries)

    return render_template('manage_all_calendars.html', calendar_entries=calendar_entries)


@calendar_routes.route('/schedule_viewing/<int:property_id>', methods=['GET', 'POST'])
@login_required
def schedule_viewing(property_id):
    property = Property.query.get_or_404(property_id)

    # Check if the user is the owner or manager
    if property.owner_id != current_user.owner_id and current_user.manager_id is None:
        abort(403)

    if request.method == 'POST':
        date_start_str = request.form.get('date_start')
        date_end_str = request.form.get('date_end')

        try:
            date_start = datetime.strptime(date_start_str, '%Y-%m-%dT%H:%M')
            date_end = datetime.strptime(date_end_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return redirect(url_for('calendar_routes.schedule_viewing', property_id=property_id))

        # Create a new calendar entry with status 'available'
        calendar_entry = Calendar(
            date_start=date_start,
            date_end=date_end,
            status='available',
            property_id=property_id,
            user_id=current_user.id
        )
        db.session.add(calendar_entry)
        db.session.commit()

        flash('Viewing scheduled successfully!', 'success')
        return redirect(url_for('calendar_routes.manage_property_calendar', property_id=property_id))

    return render_template('schedule_viewing.html', property=property)


@calendar_routes.route('/update_calendar_entry/<int:entry_id>', methods=['POST'])
@login_required
def update_calendar_entry(entry_id):
    entry = Calendar.query.get_or_404(entry_id)

    # Check if the user is the owner or manager
    if entry.property.owner_id != current_user.owner_id and current_user.manager_id is None:
        abort(403)

    new_status = request.form.get('status')
    if new_status in ('available', 'unavailable'):
        entry.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
@calendar_routes.route('/schedule_viewing/<int:property_id>', methods=['GET', 'POST'])
@login_required
def schedule_viewing(property_id):
    property = Property.query.get_or_404(property_id)

    # Check if the user is the owner or manager
    if property.owner_id != current_user.owner_id and current_user.manager_id is None:
        abort(403)

    if request.method == 'POST':
        date_start_str = request.form.get('date_start')
        date_end_str = request.form.get('date_end')

        try:
            date_start = datetime.strptime(date_start_str, '%Y-%m-%dT%H:%M')
            date_end = datetime.strptime(date_end_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid date/time format.', 'danger')
            return redirect(url_for('calendar_routes.schedule_viewing', property_id=property_id))

        # Create a new calendar entry with status 'available'
        calendar_entry = Calendar(
            date_start=date_start,
            date_end=date_end,
            status='available',
            property_id=property_id,
            user_id=current_user.id
        )
        db.session.add(calendar_entry)
        db.session.commit()

        flash('Viewing scheduled successfully!', 'success')
        return redirect(url_for('calendar_routes.manage_calendar', property_id=property_id))

    return render_template('schedule_viewing.html', property=property)