from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required
from forms import ProfileForm, ProfilePicForm, CompanyForm, SettingsForm
from models import Country, User, Currency, Company
from extensions import db
from werkzeug.utils import secure_filename
from utils.session import session_scope

import os

from routes import allowed_file


profile_routes = Blueprint('profile_routes', __name__)


@profile_routes.route('/profile_settings', methods=['GET', 'POST'])
@login_required
def profile_settings():
    try:
        if request.method == 'POST':
            # Check if this is a profile picture upload
            if 'profile_picture' in request.files:
                profile_pic_form = ProfilePicForm()
                if profile_pic_form.validate_on_submit():
                    try:
                        user = db.session.get(User, current_user.id)
                        if not user:
                            return jsonify({'success': False, 'error': 'User not found'}), 404

                        file = profile_pic_form.profile_picture.data
                        if file and allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            # Save the file
                            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                            # Update user's profile picture
                            user.profile_picture = filename
                            db.session.commit()
                            
                            return jsonify({
                                'success': True,
                                'message': 'Profile picture updated successfully'
                            })
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Profile picture upload error: {str(e)}")
                        return jsonify({
                            'success': False,
                            'error': f'Error uploading profile picture: {str(e)}'
                        }), 500
                else:
                    return jsonify({
                        'success': False,
                        'error': profile_pic_form.errors
                    }), 400
            
            # Handle main profile form submission
            else:
                form = ProfileForm(formdata=request.form, current_user=current_user)
                if form.validate_on_submit():
                    user = db.session.get(User, current_user.id)
                    if not user:
                        return jsonify({'success': False, 'error': 'User not found'}), 404

                    try:
                        # Update fields safely by checking render_kw attribute
                        if not (hasattr(form.gender, 'render_kw') and 
                               form.gender.render_kw and 
                               form.gender.render_kw.get('disabled')):
                            user.gender = form.gender.data
                        
                        if not (hasattr(form.country, 'render_kw') and 
                               form.country.render_kw and 
                               form.country.render_kw.get('disabled')):
                            user.country_id = form.country.data
                            user.currency_id = form.currency_id.data
                        
                        if not (hasattr(form.phone_number, 'render_kw') and 
                               form.phone_number.render_kw and 
                               form.phone_number.render_kw.get('readonly')):
                            user.phone_number = form.phone_number.data.strip() if form.phone_number.data else None
                        
                        if not (hasattr(form.birthday, 'render_kw') and 
                               form.birthday.render_kw and 
                               form.birthday.render_kw.get('readonly')):
                            user.birthday = form.birthday.data
                        
                        # These fields can always be updated
                        if form.email.data:
                            user.email = form.email.data.strip()
                        
                        if form.next_of_keen_contacts.data:
                            user.next_of_keen_contacts = form.next_of_keen_contacts.data.strip()

                        # Debug logging
                        current_app.logger.debug(f"Updating user {user.id}:")
                        current_app.logger.debug(f"Gender: {user.gender}")
                        current_app.logger.debug(f"Country: {user.country_id}")
                        current_app.logger.debug(f"Currency: {user.currency_id}")
                        current_app.logger.debug(f"Phone: {user.phone_number}")
                        current_app.logger.debug(f"Birthday: {user.birthday}")
                        current_app.logger.debug(f"Email: {user.email}")
                        current_app.logger.debug(f"Next of Kin: {user.next_of_keen_contacts}")

                        db.session.commit()
                        return jsonify({
                            'success': True,
                            'message': 'Profile updated successfully'
                        })
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Database error: {str(e)}")
                        return jsonify({
                            'success': False,
                            'error': f'Database error occurred: {str(e)}'
                        }), 500
                else:
                    current_app.logger.error(f"Form validation errors: {form.errors}")
                    return jsonify({
                        'success': False,
                        'error': form.errors
                    }), 400

        # GET request
        form = ProfileForm(current_user=current_user)
        profile_pic_form = ProfilePicForm()

        return render_template('profile_settings.html', 
                             form=form,
                             profile_pic_form=profile_pic_form)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in profile_settings: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@profile_routes.route('/api/get_currency/<country_id>')
@login_required
def get_currency(country_id):
    try:
        # Get country and join with currency
        currency = Currency.query.select_from(Country).join(Currency)\
            .filter(Country.id == country_id).first()
        
        if not currency:
            current_app.logger.error(f"No currency found for country: {country_id}")
            return jsonify({
                'success': False,
                'error': 'Currency not found'
            }), 404
        
        current_app.logger.debug(f"Found currency: {currency.id} for country: {country_id}")
        
        return jsonify({
            'success': True,
            'currency_id': currency.id
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching currency for country {country_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@profile_routes.route('/company', methods=['GET', 'POST'])
@login_required
def company():
    form = CompanyForm()  # Assuming you have a CompanyForm defined in forms.py

    # Check if the user already has a company
    existing_company = Company.query.filter(Company.users.contains(current_user)).first()
    if existing_company:
        # Populate the form with existing company data
        form.company_name.data = existing_company.company_name
        form.company_registration_number.data = existing_company.company_registration_number
        form.tax_number.data = existing_company.tax_number

    if form.validate_on_submit():
        if existing_company:
            flash('You already have a company added.', 'danger')
            return redirect(url_for('profile_routes.company'))

        # Create a new company instance
        new_company = Company(
            company_name=form.company_name.data,
            company_registration_number=form.company_registration_number.data,
            tax_number=form.tax_number.data
        )

        # Add the new company to the database
        db.session.add(new_company)
        db.session.commit()

        # Update the current user's company_id
        current_user.company_id = new_company.id
        db.session.commit()

        flash('Company added successfully!', 'success')
        return redirect(url_for('profile_routes.company'))

    return render_template('company_settings.html', form=form)

@profile_routes.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm(user=current_user)

    if form.validate_on_submit():
        try:
            # Log the form data for debugging
            current_app.logger.debug(f"Form data: {form.data}")

            # Update the user's system preference
            current_user.system = form.system.data
            
            # Use the session_scope context manager
            with session_scope():
                db.session.commit()
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('profile_routes.settings', success=True))
        except Exception as e:
            current_app.logger.error(f"Error updating settings: {str(e)}")
            flash('An error occurred while updating settings. Please try again.', 'danger')

    return render_template('settings.html', form=form)