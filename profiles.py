from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required
from forms import ProfileForm, ProfilePicForm, CompanyForm, SettingsForm, BankingDetailsForm
from models import Banks, Country, User, Currency, Company, BankingDetails
from extensions import db
from werkzeug.utils import secure_filename
from session import session_scope
from sqlalchemy.orm import joinedload

import os

from routes import allowed_file


profile_routes = Blueprint('profile_routes', __name__)


@profile_routes.route('/profile_settings', methods=['GET', 'POST'])
@login_required
def profile_settings():
    # if not (current_user.phone_number and current_user.birthday and current_user.gender and current_user.country_id):
    #     flash("Please complete your account setup before accessing this page.", "warning")
    #     return redirect(url_for('profile_routes.setup_account'))  
    
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

        return render_template('profile/profile_settings.html', 
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

    return render_template('profile/company_settings.html', form=form)

@profile_routes.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm(user=current_user)

    if form.validate_on_submit():
        try:
            current_app.logger.debug(f"Form data: {form.data}")
            current_user.system = form.system.data
            
            with session_scope():
                db.session.commit()
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('profile_routes.settings', success=True))
        except Exception as e:
            current_app.logger.error(f"Error updating settings: {str(e)}")
            flash('An error occurred while updating settings. Please try again.', 'danger')
    else:
        current_app.logger.error(f"Form validation errors: {form.errors}")

    return render_template('profile/settings.html', form=form)

@profile_routes.route('/banking_details/<int:banking_details_id>', methods=['GET', 'POST'])
@login_required
def banking_details(banking_details_id):
    user = User.query.options(joinedload(User.country)).get(current_user.id)
    banks = Banks.query.filter_by(country_id=user.country_id).all()
    banks_list = [(bank.id, bank.bank_name) for bank in banks]  # Prepare bank choices

    # Retrieve existing banking details for the user based on banking_details_id
    existing_banking_details = BankingDetails.query.filter_by(id=banking_details_id, user_id=current_user.id).first() if banking_details_id else None

    # Pass existing data to the form
    form = BankingDetailsForm(banks=banks_list)

    if existing_banking_details:
        form.bank_id.data = existing_banking_details.bank_id
        form.account_number.data = existing_banking_details.account_number
        form.account_holder_name.data = existing_banking_details.account_holder_name
        form.account_type.data = existing_banking_details.account_type
        form.branch.data = existing_banking_details.branch
        form.branch_code.data = existing_banking_details.branch_code
        form.account_iban.data = existing_banking_details.account_iban

    if form.validate_on_submit():
        # Retrieve the selected bank_id
        selected_bank_id = form.bank_id.data
        
        # Get the bank details from the database
        selected_bank = Banks.query.get(selected_bank_id)
        
        if not selected_bank:
            flash('Selected bank not found.', 'danger')
            return redirect(url_for('profile_routes.banking_details'))

        # Create or update BankingDetails instance
        if existing_banking_details:
            existing_banking_details.account_number = form.account_number.data
            existing_banking_details.account_holder_name = form.account_holder_name.data
            existing_banking_details.account_type = form.account_type.data
            existing_banking_details.branch = form.branch.data
            existing_banking_details.branch_code = form.branch_code.data
            existing_banking_details.account_iban = form.account_iban.data
            existing_banking_details.bank_id = selected_bank_id  
            existing_banking_details.is_primary = form.is_primary.data
            existing_banking_details.nickname = form.nickname.data
        else:
            banking_details = BankingDetails(
                account_number=form.account_number.data,
                account_holder_name=form.account_holder_name.data,
                account_type=form.account_type.data,
                branch=form.branch.data,
                branch_code=form.branch_code.data,
                account_iban=form.account_iban.data,
                user_id=current_user.id,
                bank_id=selected_bank_id,  # Set the bank_id
                is_primary=form.is_primary.data,
                nickname=form.nickname.data
            )
            db.session.add(banking_details)

        db.session.commit()
        
        # Flash message for success
        flash('Banking details added/updated successfully!', 'success')
        
        # Redirect to the banking details page for the specific banking detail
        return redirect(url_for('profile_routes.banking_details', banking_details_id=banking_details_id))

    # Check for success parameter to show popup
    success = request.args.get('success', False)
    return render_template('profile/banking_details.html', form=form, user=user, success=success, existing_banking_details=existing_banking_details)

@profile_routes.route('/banking_settings', methods=['GET', 'POST'])
@login_required
def banking_settings():
    # Retrieve existing banking details for the current user
    banking_details = BankingDetails.query.filter_by(user_id=current_user.id).all()  # Fetch user's banking details
    
    # Create an instance of the BankingDetailsForm
    form = BankingDetailsForm()

    return render_template('profile/banking_settings.html', banking_details=banking_details, form=form)  # Pass banking_details and form to the template

@profile_routes.route('/delete_banking_detail/<int:id>', methods=['POST'])
@login_required
def delete_banking_detail(id):
    # Retrieve the banking detail to be deleted
    banking_detail = BankingDetails.query.filter_by(id=id, user_id=current_user.id).first()
    
    if banking_detail:
        db.session.delete(banking_detail)
        db.session.commit()
        flash('Banking detail deleted successfully!', 'success')
    else:
        flash('Banking detail not found.', 'danger')
    
    return redirect(url_for('profile_routes.banking_settings'))

@profile_routes.route('/setup_account', methods=['GET', 'POST'])
def setup_account():
    return render_template('profile/setup_account.html')

