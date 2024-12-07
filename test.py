<<<<<<< HEAD
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, jsonify, abort
from flask_login import login_required, current_user
from accounting import allowed_file
from models import Property, Owner, Photo, Listing, RentalAgreement, Photo, Country, State
from extensions import db
from forms import PropertyDetailsForm, FeatureForm, AddressForm, PhotoForm, ListingForm
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from config import GOOGLE_MAPS_API_KEY
import os
import shutil
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField
from wtforms.validators import DataRequired, Optional
import traceback


property_routes = Blueprint('property_routes', __name__)

@property_routes.route('/property/new', methods=['GET'])
@login_required
def new_property():
    try:
        # Add debug logging at the start
        current_app.logger.debug("Entering new_property route")
        
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            current_app.logger.debug("Owner not found for user_id: %s", current_user.id)
            flash('Owner profile not found.', 'error')
            return redirect(url_for('main.dashboard'))

        # Add debug logging before template render
        current_app.logger.debug("About to render template")
        
        return render_template('property/manage_property.html',
                             property=None,
                             photos=[],
                             listing=None,
                             owner=owner)

    except ValueError as e:
        # Log the full error details
        current_app.logger.error("ValueError in new_property:")
        current_app.logger.error(str(e))
        current_app.logger.error("".join(traceback.format_exc()))
        flash('Invalid property ID format.', 'error')
        return redirect(url_for('property_routes.property_list'))
        
    except Exception as e:
        # Log the full error details
        current_app.logger.error("Unexpected error in new_property:")
        current_app.logger.error(str(e))
        current_app.logger.error("".join(traceback.format_exc()))
        flash('An unexpected error occurred.', 'error')
        return redirect(url_for('property_routes.property_list'))

@property_routes.route('/property/manage/<int:property_id>', methods=['GET'])
@login_required
def manage_property(property_id):
    try:
        # Get the owner
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            flash('Owner profile not found.', 'error')
            return redirect(url_for('main.dashboard'))

        # Get the property
        property = Property.query.get_or_404(property_id)
        
        # Verify ownership
        if property.owner_id != owner.id:
            flash('You do not have permission to view this property.', 'error')
            return redirect(url_for('property_routes.property_list'))

        # Get photos and listing
        photos = Photo.query.filter_by(property_id=property.id).all()
        listing = Listing.query.filter_by(property_id=property.id).first()

        return render_template('property/manage_property.html',
                             property=property,
                             photos=photos,
                             listing=listing,
                             owner=owner)

    except Exception as e:
        current_app.logger.error(f"Error in manage_property: {str(e)}")
        flash('An error occurred while loading the property.', 'error')
        return redirect(url_for('property_routes.property_list'))


@property_routes.route('/property/edit_details/<property_id>', methods=['GET', 'POST'])
@login_required
def edit_details(property_id):
    try:
        current_app.logger.info("=== Request Debug Info ===")
        current_app.logger.info(f"Full URL: {request.url}")
        current_app.logger.info(f"Method: {request.method}")
        current_app.logger.info(f"Property ID: {property_id}")
        
        # Get the current user's owner record first
        current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not current_user_owner:
            message = 'User is not registered as an owner'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': message}), 403
            flash(message, 'error')
            return redirect(url_for('main.dashboard'))
        
        # Handle GET request
        if request.method == 'GET':
            if property_id == 'new':
                property = None
                form = PropertyDetailsForm()
            else:
                property = Property.query.get_or_404(property_id)
                if property.owner_id != current_user_owner.id:
                    flash('You do not have permission to edit this property.', 'error')
                    return redirect(url_for('property_routes.property_list'))
                form = PropertyDetailsForm(obj=property)
            
            return render_template('property/edit_details.html',
                                form=form,
                                property=property,
                                is_new=(property_id == 'new'))
        
        # Handle POST request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        form = PropertyDetailsForm()
        
        if form.validate_on_submit():
            print("Form data:", form.data)  # Log the form data
            try:
                # Get or create property
                if property_id == 'new':
                    property = Property(
                        owner_id=current_user_owner.id,
                        created_date=datetime.utcnow()
                    )
                    db.session.add(property)
                    message = 'Property created successfully'
                else:
                    property = Property.query.get_or_404(property_id)
                    if property.owner_id != current_user_owner.id:
                        return abort(403)
                    message = 'Property updated successfully'

                # Update property with form data
                form.populate_obj(property)
                db.session.commit()
                
                current_app.logger.info(f"Successfully saved property {property.id}")
                
                if is_ajax:
                    return jsonify({
                        'success': True,
                        'message': message,
                        'property_id': property.id,
                        'redirect_url': url_for('property_routes.manage_property', property_id=property.id)
                    })
                else:
                    flash(message, 'success')
                    return redirect(url_for('property_routes.manage_property', property_id=property.id))
                    
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Database error: {str(e)}")
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'message': 'Database error occurred'
                    }), 500
                else:
                    flash('Database error occurred', 'error')
                    return redirect(url_for('property_routes.property_list'))
        else:
            # Form validation failed
            if is_ajax:
                return jsonify({
                    'success': False,
                    'message': 'Form validation failed',
                    'errors': form.errors
                }), 400
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'{field}: {error}', 'error')
                return render_template('property/edit_details.html',
                                    form=form,
                                    property=property)

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        if is_ajax:
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred'
            }), 500
        else:
            flash('An unexpected error occurred', 'error')
            return redirect(url_for('property_routes.property_list'))


@property_routes.route('/property/property_list')
@property_routes.route('/properties')
@login_required
def property_list():
    """Display list of all properties owned by the current user"""
    current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
    if not current_user_owner:
        abort(403)

    properties_data = []
    properties = Property.query.filter_by(owner_id=current_user_owner.id).all()

    for property in properties:
        try:
            # Get latest listing
            latest_listing = db.session.query(Listing).filter(
                Listing.property_id == property.id
            ).order_by(
                Listing.date_created.desc()
            ).first()

            # Get latest rental agreement
            latest_agreement = db.session.query(
                RentalAgreement.status,
                RentalAgreement.date_created
            ).filter(
                RentalAgreement.property_id == property.id
            ).order_by(
                RentalAgreement.date_created.desc()
            ).first()

            # Determine status based on conditions
            if latest_agreement and latest_agreement.status == 'accepted':
                listing_status = 'Occupied'
                if latest_listing and latest_listing.status:
                    latest_listing.status = False  # Ensure listing is inactive if property is occupied
                    db.session.commit()
            elif latest_listing:
                if latest_listing.status is True:
                    if latest_agreement and latest_agreement.status == 'pending':
                        listing_status = 'Pending'  # Active enquiry
                    else:
                        listing_status = 'Listed'  # Available to tenants
                else:
                    listing_status = 'Unlisted'  # Not available
            else:
                listing_status = 'Unlisted'  # No listing exists

            # Get thumbnail
            thumbnail = None
            if property.photos:
                thumbnail = next((photo for photo in property.photos if photo.is_thumbnail), 
                               property.photos[0] if property.photos else None)

            properties_data.append({
                'property': property,
                'thumbnail': thumbnail,
                'listing_status': listing_status,
                'listing': latest_listing
            })

        except Exception as e:
            current_app.logger.error(f"Error processing property {property.id}: {str(e)}")
            db.session.rollback()
            properties_data.append({
                'property': property,
                'thumbnail': property.thumbnail,
                'listing_status': 'Error',
                'listing': None
            })

    form = FlaskForm()  # Create an empty form for CSRF protection
    return render_template('property/property_list.html', properties=properties_data, form=form)


@property_routes.route('/property/edit_features/<property_id>', methods=['GET', 'POST'])
@login_required
def edit_features(property_id):
    """Edit property features"""
    property = Property.query.get_or_404(property_id)
    # Get the owner record for the current user
    current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
    
    # Check if current user is the owner
    if not current_user_owner or property.owner_id != current_user_owner.id:
        abort(403)

    form = FeatureForm()

    if request.method == 'GET':
        # Pre-populate form with existing property features
        form.swimming_pool.data = property.swimming_pool
        form.garden.data = property.garden
        form.air_conditioning.data = property.air_conditioning
        form.heating.data = property.heating
        form.gym.data = property.gym
        form.laundry.data = property.laundry
        form.fireplace.data = property.fireplace
        form.balcony.data = property.balcony
        form.pet_friendly.data = property.pet_friendly
        form.bbq_area.data = property.bbq_area
        form.jacuzzi.data = property.jacuzzi
        form.tennis_court.data = property.tennis_court

    if form.validate_on_submit():
        # Update property features
        property.swimming_pool = form.swimming_pool.data
        property.garden = form.garden.data
        property.air_conditioning = form.air_conditioning.data
        property.heating = form.heating.data
        property.gym = form.gym.data
        property.laundry = form.laundry.data
        property.fireplace = form.fireplace.data
        property.balcony = form.balcony.data
        property.pet_friendly = form.pet_friendly.data
        property.bbq_area = form.bbq_area.data
        property.jacuzzi = form.jacuzzi.data
        property.tennis_court = form.tennis_court.data

        try:
            db.session.commit()
            flash('Property features updated successfully!', 'success')
            return redirect(url_for('property_routes.manage_property', property_id=property.id))
        except Exception as e:
            db.session.rollback()
            flash('Error updating property features.', 'danger')
            current_app.logger.error(f"Error updating property features: {str(e)}")

    return render_template('property/edit_features.html', property=property, form=form)

@property_routes.route('/property/edit_address/<int:property_id>', methods=['GET', 'POST'])
@login_required
def edit_address(property_id):
    try:
        current_app.logger.info(f"Starting edit_address for property_id: {property_id}")
        
        # First get the owner
        owner = db.session.query(Owner).filter(
            Owner.user_id == current_user.id
        ).first()

        current_app.logger.info(f"Owner query result: {owner}")

        if not owner:
            current_app.logger.error(f"Owner not found for user_id: {current_user.id}")
            flash('Owner profile not found.', 'error')
            return redirect(url_for('property_routes.property_list'))

        # Get the specific property with explicit join and debug logging
        property_query = (db.session.query(Property)
                         .filter(Property.id == property_id)
                         .filter(Property.owner_id == owner.id))
        
        current_app.logger.debug(f"Property query SQL: {str(property_query)}")
        property = property_query.first()
        current_app.logger.info(f"Property query result: {property}")

        if not property:
            current_app.logger.warning(
                f"No property found with ID {property_id} for owner {owner.id}. "
                f"Owner's properties: {[p.id for p in owner.properties]}"
            )
            flash('Property not found or you do not have permission to edit it.', 'error')
            return redirect(url_for('property_routes.property_list'))

        # Get API key from config with debug logging
        api_key = current_app.config.get('GOOGLE_MAPS_API_KEY')
        current_app.logger.debug(f"API key present: {bool(api_key)}")

        if not api_key:
            current_app.logger.error("Google Maps API key is not configured")
            flash('Map functionality is currently unavailable.', 'error')
            return redirect(url_for('property_routes.property_list'))

        # Create form and debug log its creation
        form = AddressForm()
        current_app.logger.debug("Form created successfully")

        # If GET request, populate form with existing data
        if request.method == 'GET':
            current_app.logger.info("Populating form with existing data")
            current_app.logger.debug(f"Property address data: {property.street_address}, {property.suburb}, {property.city}")
            
            form.street_address.data = property.street_address or ''
            form.building.data = property.building or ''
            form.door_number.data = property.door_number or ''
            form.suburb.data = property.suburb or ''
            form.city.data = property.city or ''
            form.state_id.data = property.state_id or ''
            form.country_id.data = property.country_id or ''
            form.latitude.data = str(property.latitude) if property.latitude else ''
            form.longitude.data = str(property.longitude) if property.longitude else ''

            current_app.logger.debug("Form populated successfully")

        if form.validate_on_submit():
            try:
                current_app.logger.info("Processing form submission")
                current_app.logger.debug(f"Form data: {form.data}")

                # Check if state exists in database, if not create it
                state = db.session.query(State).filter_by(id=form.state_id.data).first()
                if not state and form.state_id.data:
                    state = State(
                        id=form.state_id.data,
                        state=form.city.data,  # Use city name as state name if unknown
                        country_id=form.country_id.data
                    )
                    db.session.add(state)
                    current_app.logger.info(f"Created new state: {state.id}")

                # Check if country exists, if not create it
                country = db.session.query(Country).filter_by(id=form.country_id.data).first()
                if not country and form.country_id.data:
                    country = Country(
                        id=form.country_id.data,
                        country=form.country_id.data  # Use country code as name temporarily
                    )
                    db.session.add(country)
                    current_app.logger.info(f"Created new country: {country.id}")

                # Update property with form data
                property.street_address = form.street_address.data
                property.building = form.building.data
                property.door_number = form.door_number.data
                property.suburb = form.suburb.data
                property.city = form.city.data
                property.state_id = form.state_id.data if form.state_id.data else None
                property.country_id = form.country_id.data if form.country_id.data else None
                property.latitude = float(form.latitude.data) if form.latitude.data else None
                property.longitude = float(form.longitude.data) if form.longitude.data else None

                current_app.logger.debug(f"Attempting to save property with state_id: {property.state_id}, country_id: {property.country_id}")
                
                db.session.commit()
                current_app.logger.info(f"Successfully updated address for property {property.id}")
                flash('Property address updated successfully!', 'success')
                return redirect(url_for('property_routes.manage_property', property_id=property.id))
            except Exception as e:
                current_app.logger.error(f"Error updating property address: {str(e)}", exc_info=True)
                db.session.rollback()
                flash('Error updating property address. Please ensure all location data is valid.', 'error')

        current_app.logger.info("Rendering edit_address template")
        return render_template('property/edit_address.html',
                             property=property,
                             form=form,
                             api_key=api_key)

    except Exception as e:
        current_app.logger.error(f"Unexpected error in edit_address: {str(e)}", exc_info=True)
        db.session.rollback()
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('property_routes.property_list'))


@property_routes.route('/property/edit_photos/<property_id>', methods=['GET', 'POST'])
@login_required
def edit_photos(property_id):
    property = Property.query.get_or_404(property_id)
    current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
    
    if not current_user_owner or property.owner_id != current_user_owner.id:
        abort(403)

    form = PhotoForm()

    if form.validate_on_submit():
        try:
            # Handle thumbnail upload
            if form.thumbnail.data:
                current_app.logger.info("Processing thumbnail upload...")
                
                # Remove old thumbnail
                old_thumbnail = Photo.query.filter_by(property_id=property.id, is_thumbnail=True).first()
                if old_thumbnail:
                    current_app.logger.info(f"Removing old thumbnail: {old_thumbnail.file_path}")
                    try:
                        old_path = os.path.join(current_app.static_folder, old_thumbnail.file_path)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                        db.session.delete(old_thumbnail)
                        current_app.logger.info("Old thumbnail removed successfully")
                    except Exception as e:
                        current_app.logger.error(f"Error removing old thumbnail: {str(e)}")

                # Process new thumbnail
                original_filename = secure_filename(form.thumbnail.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{original_filename}"
                
                # Create paths
                relative_path = f"uploads/property_photos/{property.id}/{filename}"
                upload_path = os.path.join(current_app.static_folder, 'uploads/property_photos', str(property.id))
                full_path = os.path.join(upload_path, filename)
                
                # Ensure directory exists
                os.makedirs(upload_path, exist_ok=True)
                
                # Save file
                try:
                    form.thumbnail.data.save(full_path)
                    current_app.logger.info(f"Thumbnail saved to: {full_path}")
                except Exception as e:
                    current_app.logger.error(f"Error saving thumbnail file: {str(e)}")
                    raise

                # Create database record
                try:
                    thumbnail = Photo(
                        file_path=relative_path,
                        filename=original_filename,  # Add the original filename
                        property_id=property.id,
                        is_thumbnail=True,
                        order=0
                    )
                    db.session.add(thumbnail)
                    current_app.logger.info("Thumbnail record added to session")
                except Exception as e:
                    current_app.logger.error(f"Error creating thumbnail record: {str(e)}")
                    raise

            # Handle regular photos
            if form.photos.data:
                for photo in form.photos.data:
                    if photo.filename:
                        current_app.logger.info(f"Processing regular photo: {photo.filename}")
                        
                        original_filename = secure_filename(photo.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"{timestamp}_{original_filename}"
                        
                        relative_path = f"uploads/property_photos/{property.id}/{filename}"
                        upload_path = os.path.join(current_app.static_folder, 'uploads/property_photos', str(property.id))
                        full_path = os.path.join(upload_path, filename)
                        
                        os.makedirs(upload_path, exist_ok=True)
                        
                        try:
                            photo.save(full_path)
                            current_app.logger.info(f"Photo saved to: {full_path}")
                            
                            photo_record = Photo(
                                file_path=relative_path,
                                filename=original_filename,  # Add the original filename
                                property_id=property.id,
                                is_thumbnail=False,
                                order=0
                            )
                            db.session.add(photo_record)
                            current_app.logger.info("Photo record added to session")
                        except Exception as e:
                            current_app.logger.error(f"Error processing photo: {str(e)}")
                            raise

            # Commit all changes
            try:
                db.session.commit()
                current_app.logger.info("All changes committed successfully")
                flash('Photos uploaded successfully!', 'success')
                return redirect(url_for('property_routes.manage_property', property_id=property.id))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error committing changes: {str(e)}")
                flash('Error uploading photos.', 'danger')
                raise

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Upload error: {type(e).__name__} - {str(e)}")
            flash('Error uploading photos.', 'danger')

    # Debug existing photos
    current_app.logger.info(f"\nExisting photos for property {property_id}:")
    for photo in property.photos:
        current_app.logger.info(f"  Path: {photo.file_path}")
        full_path = os.path.join(current_app.static_folder, photo.file_path)
        current_app.logger.info(f"  Exists: {os.path.exists(full_path)}")

    return render_template('property/edit_photos.html', 
                         property=property, 
                         form=form,
                         debug=current_app.debug)

@property_routes.route('/property/delete_photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    try:
        # Get the photo
        photo = Photo.query.get_or_404(photo_id)
        
        # Get the property
        property = Property.query.get_or_404(photo.property_id)
        
        # Verify ownership
        current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not current_user_owner or property.owner_id != current_user_owner.id:
            flash('You do not have permission to delete this photo.', 'error')
            return redirect(url_for('property_routes.manage', property_id=property.id))

        # Delete the photo file
        if photo.filename:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], photo.filename)
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete from database
        db.session.delete(photo)
        db.session.commit()

        flash('Photo deleted successfully', 'success')
        return redirect(url_for('property_routes.manage_property', property_id=property.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting photo: {str(e)}")
        flash('An error occurred while deleting the photo', 'error')
        return redirect(url_for('property_routes.manage_property', property_id=photo.property_id))

@property_routes.route('/property/view/<property_id>')
@login_required
def view_property(property_id):
    """Display detailed view of a property"""
    property = Property.query.get_or_404(property_id)
    
    # Get the owner record for the current user
    current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
    
    # Check if current user is the owner
    if not current_user_owner or property.owner_id != current_user_owner.id:
        abort(403)
        
    return render_template('property/view_property.html', property=property)

@property_routes.route('/check_api_key')
def check_api_key():
    key = current_app.config.get('GOOGLE_MAPS_API_KEY')
    return f"API Key exists: {bool(key)}, First few chars: {key[:10] if key else 'None'}"

@property_routes.route('/property/create_listing/<int:property_id>', methods=['GET', 'POST'])
@login_required
def create_listing(property_id):
    # Fetch the property using the property_id
    property = Property.query.get_or_404(property_id)

    # Instantiate the form
    form = ListingForm()

    if request.method == 'GET':
        # Render the form for creating a listing
        return render_template('property/create_listing.html', property=property, form=form)

    # Handle POST request for creating a listing
    if form.validate_on_submit():  # Validate the form
        try:
            # Create a new listing
            new_listing = Listing(
                property_id=property_id,
                deposit=form.deposit.data,
                admin_fee=form.admin_fee.data,
                listing_type=form.listing_type.data,
                monthly_rental=form.monthly_rental.data,
                available_start_date=form.available_start_date.data,
                available_end_date=form.available_end_date.data,
                viewing_availibility_dates=form.viewing_availibility_dates.data,  # Capture as string
                status=1,
                date_created=datetime.utcnow()
            )
            db.session.add(new_listing)
            db.session.commit()  # Commit the transaction
            
            return jsonify({"message": "Listing created successfully!"}), 201

        except SQLAlchemyError as e:
            db.session.rollback()  # Rollback the transaction on error
            current_app.logger.error(f"Error creating listing: {str(e)}")  # Log the error
            return jsonify({"error": "An error occurred while creating the listing."}), 500
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}")  # Log unexpected errors
            return jsonify({"error": "An unexpected error occurred."}), 500
    else:
        # Log form errors for debugging
        current_app.logger.error(f"Form errors: {form.errors}")
        return jsonify({"errors": form.errors}), 400

@property_routes.route('/property/set_thumbnail/<int:photo_id>', methods=['POST'])
@login_required
def set_thumbnail(photo_id):
    """Set a photo as the property thumbnail"""
    photo = Photo.query.get_or_404(photo_id)
    property = Property.query.get(photo.property_id)
    
    # Check ownership
    current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
    if not current_user_owner or property.owner_id != current_user_owner.id:
        abort(403)

    try:
        # Remove current thumbnail flag
        current_thumbnail = Photo.query.filter_by(
            property_id=property.id, 
            is_thumbnail=True
        ).first()
        
        if current_thumbnail:
            current_thumbnail.is_thumbnail = False
            
        # Set new thumbnail
        photo.is_thumbnail = True
        db.session.commit()
        
        flash('Thumbnail updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error setting thumbnail: {str(e)}")
        flash('Error updating thumbnail.', 'danger')
    
    return redirect(url_for('property_routes.edit_photos', property_id=property.id))

@property_routes.route('/property/toggle_listing/<property_id>', methods=['POST'])
@login_required
def toggle_listing(property_id):
    property = Property.query.get_or_404(property_id)
    current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
    
    if not current_user_owner or property.owner_id != current_user_owner.id:
        abort(403)
        
    try:
        # Find active listing
        active_listing = Listing.query.filter_by(
            property_id=property.id, 
            status=True
        ).first()
        
        if active_listing:
            active_listing.status = False
            db.session.commit()
            flash('Property has been unlisted successfully.', 'success')
        else:
            flash('No active listing found for this property.', 'warning')
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error unlisting property: {str(e)}")
        flash('Error unlisting property.', 'danger')
        
    return redirect(url_for('property_routes.property_list'))

@property_routes.route('/property/duplicate/<property_id>')
@login_required
def duplicate_property(property_id):
    # Get original property
    original = Property.query.get_or_404(property_id)
    current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
    
    # Check ownership
    if not current_user_owner or original.owner_id != current_user_owner.id:
        abort(403)
        
    try:
        # Create new property with copied attributes
        new_property = Property(
            owner_id=original.owner_id,
            title=f"Copy of {original.title}",
            description=original.description,
            type=original.type,
            sqm=original.sqm,
            bedroom=original.bedroom,
            bathroom=original.bathroom,
            garage=original.garage,
            kitchen=original.kitchen,
            
            # Copy amenities
            swimming_pool=original.swimming_pool,
            garden=original.garden,
            air_conditioning=original.air_conditioning,
            heating=original.heating,
            gym=original.gym,
            laundry=original.laundry,
            fireplace=original.fireplace,
            balcony=original.balcony,
            pet_friendly=original.pet_friendly,
            bbq_area=original.bbq_area,
            jacuzzi=original.jacuzzi,
            tennis_court=original.tennis_court,
            
            # Copy address
            street_address=original.street_address,
            building=original.building,
            door_number=original.door_number,
            suburb=original.suburb,
            city=original.city,
            state_id=original.state_id,
            country_id=original.country_id,
            latitude=original.latitude,
            longitude=original.longitude
        )
        
        db.session.add(new_property)
        db.session.flush()  # Get the new ID
        
        # Copy photos
        for photo in original.photos:
            # Create new filename with new property ID
            original_filename = photo.filename
            new_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_filename}"
            
            # Copy the physical file
            original_path = os.path.join(current_app.root_path, 'static', photo.file_path)
            new_relative_path = f"uploads/property_photos/{new_property.id}/{new_filename}"
            new_path = os.path.join(current_app.root_path, 'static', new_relative_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            
            # Copy the file
            shutil.copy2(original_path, new_path)
            
            # Create new photo record
            new_photo = Photo(
                property_id=new_property.id,
                file_path=new_relative_path,
                filename=new_filename,
                is_thumbnail=photo.is_thumbnail,
                order=photo.order
            )
            db.session.add(new_photo)
        
        db.session.commit()
        flash('Property duplicated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error duplicating property: {str(e)}")
        flash('Error duplicating property.', 'danger')
        
    return redirect(url_for('property_routes.property_list'))

@property_routes.route('/property/delete/<int:property_id>', methods=['POST'])
@login_required
def delete_property(property_id):
    try:
        # Get the owner record for the current user
        current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
        
        if not current_user_owner:
            return jsonify({'error': 'User is not registered as an owner'}), 403

        # Get the property
        property = Property.query.get_or_404(property_id)
        
        # Check ownership
        if property.owner_id != current_user_owner.id:
            return jsonify({'error': 'Unauthorized access'}), 403
            
        # Check if property is occupied
        latest_agreement = RentalAgreement.query.filter_by(
            property_id=property_id,
            status='accepted'
        ).first()
        
        if latest_agreement:
            return jsonify({'error': 'Cannot delete an occupied property'}), 400

        try:
            # Delete associated photos
            if property.photos:
                for photo in property.photos:
                    try:
                        file_path = os.path.join(current_app.static_folder, photo.file_path)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        current_app.logger.error(f"Error deleting photo file: {str(e)}")
                    db.session.delete(photo)

            # Delete the photos directory if it exists
            photo_dir = os.path.join(current_app.static_folder, f'uploads/property_photos/{property_id}')
            if os.path.exists(photo_dir):
                shutil.rmtree(photo_dir)

            # Delete associated listings
            Listing.query.filter_by(property_id=property_id).delete()

            # Delete associated rental agreements
            RentalAgreement.query.filter_by(property_id=property_id).delete()

            # Delete the property
            db.session.delete(property)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Property deleted successfully',
                'redirect_url': url_for('property_routes.property_list')
            }), 200

        except Exception as e:
            db.session.rollback()
            raise e

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting property: {str(e)}")
        return jsonify({
            'error': str(e),
            'message': 'Failed to delete property'
        }), 400

@property_routes.route('/property/toggle_listing_status/<int:property_id>', methods=['POST'])
@login_required
def toggle_listing_status(property_id):
    try:
        property = Property.query.get_or_404(property_id)
        current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
        
        if not current_user_owner or property.owner_id != current_user_owner.id:
            abort(403)

        # Get latest listing
        latest_listing = Listing.query.filter_by(
            property_id=property_id
        ).order_by(Listing.date_created.desc()).first()

        # Get latest rental agreement
        latest_agreement = RentalAgreement.query.filter_by(
            property_id=property_id
        ).order_by(RentalAgreement.date_created.desc()).first()

        # Determine status based on conditions
        if latest_agreement and latest_agreement.status == 'accepted':
            listing_status = 'Occupied'
            if latest_listing and latest_listing.status:
                latest_listing.status = False  # Ensure listing is inactive if property is occupied
                db.session.commit()
        elif latest_listing:
            if latest_listing.status is True:
                if latest_agreement and latest_agreement.status == 'pending':
                    listing_status = 'Pending'  # Active enquiry
                else:
                    listing_status = 'Listed'  # Available to tenants
            else:
                listing_status = 'Unlisted'  # Not available
        else:
            listing_status = 'Unlisted'  # No listing exists

        # Redirect to the correct endpoint
        return redirect(url_for('property_routes.property_list'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling listing status: {str(e)}")
        flash('Error updating listing status.', 'danger')
        return redirect(url_for('property_routes.property_list'))

@property_routes.route('/property/<int:property_id>/upload-photos', methods=['POST'])
@login_required
def upload_photos(property_id):
    if 'photos' not in request.files:
        flash('No file part', 'error')
        return redirect(request.referrer)
    
    photos = request.files.getlist('photos')
    
    if not photos or all(photo.filename == '' for photo in photos):
        flash('No selected file', 'error')
        return redirect(request.referrer)

    try:
        property = Property.query.get_or_404(property_id)
        
        # Check if there's already a thumbnail
        existing_thumbnail = Photo.query.filter_by(
            property_id=property_id, 
            is_thumbnail=True
        ).first()
        
        for index, photo in enumerate(photos):
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'property_photos', filename)
                photo.save(filepath)
                
                # Create photo record in database
                new_photo = Photo(
                    property_id=property_id,
                    file_path=os.path.join('uploads', 'property_photos', filename),
                    filename=filename,
                    # Set as thumbnail if it's the first photo and no thumbnail exists
                    is_thumbnail=(index == 0 and not existing_thumbnail)
                )
                db.session.add(new_photo)
        
        db.session.commit()
        flash('Photos uploaded successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error uploading photos: {str(e)}', 'error')
    
    return redirect(url_for('property_routes.edit_photos', property_id=property_id))

@property_routes.route('/property/edit_listing/<int:property_id>', methods=['GET', 'POST'])
@login_required
def edit_listing(property_id):
    """Edit the listing details for a property"""
    # Fetch the property and its listing
    property = Property.query.get_or_404(property_id)
    listing = Listing.query.filter_by(property_id=property_id).first()

    # Check if the listing exists
    if not listing:
        flash('No listing found for this property.', 'error')
        return redirect(url_for('property_routes.property_list'))

    form = ListingForm(obj=listing)  # Prepopulate the form with existing listing data

    if form.validate_on_submit():
        try:
            # Update listing details
            listing.deposit = form.deposit.data
            listing.admin_fee = form.admin_fee.data
            listing.listing_type = form.listing_type.data
            listing.monthly_rental = form.monthly_rental.data
            listing.available_start_date = form.available_start_date.data
            listing.available_end_date = form.available_end_date.data
            listing.viewing_availibility_dates = form.viewing_availibility_dates.data
            
            db.session.commit()  # Commit the changes
            flash('Listing updated successfully!', 'success')
            return redirect(url_for('property_routes.manage_property', property_id=property_id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating listing: {str(e)}")
            flash('Error updating listing.', 'danger')

    return render_template('property/edit_listing.html', property=property, form=form)
=======
from flask import Blueprint, jsonify, request, current_app, render_template, session, flash, redirect, url_for
from models import Currency, User, db, Transaction, Property
from werkzeug.utils import secure_filename
import os
from property import properties
from utils.document_processor import DocumentProcessor
from datetime import datetime, timedelta
from flask_login import login_required
from app_constants import ACCOUNTS, DUAL_CLASSIFICATION_ITEMS, MAIN_CATEGORIES, SUBCATEGORIES, ACCOUNT_CLASSIFICATIONS, EXPENSE_CLASSIFICATIONS
from utils.document_processor import DocumentProcessor
from decimal import Decimal
from flask_login import current_user
from models import Owner, Property
from flask_wtf.csrf import generate_csrf
import spacy
from fuzzywuzzy import fuzz
from forms import PortfolioTransactionsForm, TransactionForm, TransactionFilterForm
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound
from sqlalchemy.exc import SQLAlchemyError
import logging
from functools import wraps
from utils.document_processor import DocumentProcessor
import re
import pdfplumber  # Better text extraction
import uuid
from typing import Dict, List
from flask_paginate import Pagination, get_page_args
from sqlalchemy import desc
from sqlalchemy.sql import extract, func
from dataclasses import asdict

# Set up logging
logger = logging.getLogger(__name__)

class TransactionError(Exception):
    """Custom exception for transaction-related errors"""
    pass

# Create a blueprint for transaction routes
transaction_routes = Blueprint('transaction_routes', __name__, url_prefix='/transactions')

def classify_account(account_name):
    """
    Classify an account based on ACCOUNTS structure.
    Returns tuple of (main_category, sub_category, account_name)
    """
    # Normalize the account name for comparison
    normalized_name = account_name.strip()
    
    # First check if it's a direct match in ACCOUNTS
    for category, accounts in ACCOUNTS.items():
        if normalized_name in accounts:
            main_cat, sub_cat = get_category_classification(category)
            return main_cat, sub_cat, normalized_name
    
    # If no exact match, try fuzzy matching
    best_match = None
    highest_ratio = 0
    best_category = None
    
    for category, accounts in ACCOUNTS.items():
        for account in accounts:
            ratio = fuzz.ratio(normalized_name.lower(), account.lower())
            if ratio > highest_ratio and ratio > 80:  # 80% similarity threshold
                highest_ratio = ratio
                best_match = account
                best_category = category
    
    if best_match:
        main_cat, sub_cat = get_category_classification(best_category)
        return main_cat, sub_cat, best_match
    
    return 'Unknown', 'Uncategorized', normalized_name

def get_category_classification(category):
    """
    Maps account categories to main_category and sub_category.
    """
    category_mapping = {
        'ASSETS': ('Assets', 'Current Assets'),
        'LIABILITIES': ('Liabilities', 'Current Liabilities'),
        'ADMINISTRATIVE': ('Expenses', 'Operating Expenses (Administrative)'),
        'INSURANCE': ('Expenses', 'Operating Expenses (Insurance)'),
        'PROFESSIONAL_FEES': ('Expenses', 'Operating Expenses (Professional Fees)'),
        'REPAIRS_MAINTENANCE': ('Expenses', 'Operating Expenses (Repairs and Maintenance)'),
        'MARKETING': ('Expenses', 'Operating Expenses (Marketing)'),
        'PROPERTY_TAXES': ('Expenses', 'Operating Expenses (Property Taxes)'),
        'SECURITY': ('Expenses', 'Operating Expenses (Security)'),
        'UTILITIES': ('Expenses', 'Operating Expenses (Utilities)'),
        'COMMON_AREA': ('Expenses', 'Operating Expenses (Common Area)'),
        'RENT': ('Expenses', 'Operating Expenses (Rent)'),
        'FINANCIAL': ('Expenses', 'Financial Expenses')
    }
    
    return category_mapping.get(category, ('Unknown', 'Uncategorized'))

# Helper function to get all accounts for a given main category
def get_accounts_by_main_category(main_category):
    """Get all accounts that belong to a specific main category."""
    return [
        account for account, classification in ACCOUNTS.items()
        if classification[0] == main_category
    ]

# Helper function to get all accounts for a given subcategory
def get_accounts_by_subcategory(subcategory):
    """Get all accounts that belong to a specific subcategory."""
    return [
        account for account, classification in ACCOUNTS.items()
        if classification[1] == subcategory
    ]

# Helper function to validate classification
def is_valid_classification(main_category, sub_category):
    """Check if a main_category and sub_category combination is valid."""
    return (
        main_category in MAIN_CATEGORIES and
        sub_category in SUBCATEGORIES.get(main_category, [])
    )

@transaction_routes.route('/transactions/classify', methods=['GET'])
def classify_transactions():
    """Classify transactions into account classifications with optional pagination."""
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Fetch transactions with pagination
    transactions = Transaction.query.paginate(page=page, per_page=per_page, error_out=False)
    
    if not transactions.items:
        return jsonify({"message": "No transactions found"}), 404

    classified_transactions = []

    for transaction in transactions.items:
        classification = classify_account(transaction.account)
        classified_transactions.append({
            "id": transaction.id,
            "date": transaction.date,
            "amount": float(transaction.amount),
            "account": transaction.account,
            "description": transaction.description,
            "document": transaction.document,
            "classification": classification
        })

    response = {
        "classified_transactions": classified_transactions,
        "page": transactions.page,
        "total_pages": transactions.pages,
        "total_transactions": transactions.total
    }

    return jsonify(response), 200

def save_temp_file(file):
    """Save uploaded file to temporary location"""
    if not file:
        raise ValueError("No file provided")
        
    filename = secure_filename(file.filename)
    temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{filename}")
    
    # Ensure temp directory exists
    os.makedirs(temp_dir, exist_ok=True)
    
    # Add debug logging
    current_app.logger.debug(f"Saving file {filename} to {temp_path}")
    
    file.save(temp_path)
    return temp_path

def allowed_file(filename):
    """Check if the file extension is allowed"""
    if not filename:
        return False
        
    ALLOWED_EXTENSIONS = {'pdf', 'csv', 'xlsx', 'xls'}
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    current_app.logger.debug(f"Checking file extension: {extension}")
    return extension in ALLOWED_EXTENSIONS

@transaction_routes.route('/transactions/upload', methods=['POST'])
@login_required
def upload_transactions():
    try:
        # Add debug logging
        current_app.logger.debug("Starting upload_transactions")
        
        if 'transactionFile' not in request.files:
            current_app.logger.warning("No file provided in request")
            return jsonify({
                'status': 'error',
                'message': 'No file provided'
            }), 400

        file = request.files['transactionFile']
        if file.filename == '':
            current_app.logger.warning("Empty filename provided")
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            current_app.logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid file type'
            }), 400

        # Process the file and extract transactions
        temp_path = save_temp_file(file)
        current_app.logger.debug(f"Saved temp file to: {temp_path}")
        
        processor = DocumentProcessor()
        extracted_data = processor.process_document(temp_path)
        current_app.logger.debug(f"Extracted {len(extracted_data)} transactions")
        
        # Clean up temp file
        try:
            os.remove(temp_path)
            current_app.logger.debug("Cleaned up temp file")
        except Exception as e:
            current_app.logger.warning(f"Failed to remove temp file: {str(e)}")

        # Format transactions for response
        formatted_transactions = []
        for trans in extracted_data:
            try:
                formatted_trans = {
                    'transaction_date': trans['transaction_date'].strftime('%Y-%m-%d') if isinstance(trans['transaction_date'], datetime) else trans['transaction_date'],
                    'description': trans.get('description', ''),
                    'debit_amount': float(trans.get('debit_amount', 0) or 0),
                    'credit_amount': float(trans.get('credit_amount', 0) or 0),
                    'main_category': trans.get('main_category', ''),
                    'sub_category': trans.get('sub_category', ''),
                    'account': trans.get('account', ''),
                    'is_reconciled': False
                }
                formatted_transactions.append(formatted_trans)
            except Exception as e:
                current_app.logger.error(f"Error formatting transaction: {str(e)}")
                continue

        # Store in session for later use
        session['pending_transactions'] = formatted_transactions
        current_app.logger.debug("Stored transactions in session")

        return jsonify({
            'status': 'success',
            'message': f'Successfully extracted {len(formatted_transactions)} transactions',
            'transactions': formatted_transactions
        }), 200

    except Exception as e:
        current_app.logger.error(f"Upload failed: {str(e)}")
        current_app.logger.exception("Full traceback:")  # Log full traceback
        return jsonify({
            'status': 'error',
            'message': f'Failed to process file: {str(e)}'
        }), 400

@transaction_routes.route('/transactions/commit', methods=['POST'])
@login_required
def commit_transactions():
    try:
        transactions_data = request.json.get('transactions')
        if not transactions_data:
            return jsonify({
                'status': 'error',
                'message': 'No transactions provided'
            }), 400

        # Save transactions to database
        saved_transactions = save_transactions_to_db(transactions_data, current_user.id)
        
        # Clear pending transactions from session
        session.pop('pending_transactions', None)
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully saved {len(saved_transactions)} transactions',
            'transactions': [t.to_dict() for t in saved_transactions]
        }), 200

    except Exception as e:
        logger.error(f"Failed to commit transactions: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

def process_file(file_path, file_extension):
    """Process uploaded file based on its type"""
    try:
        if file_extension == 'pdf':
            return process_pdf_file(file_path)
        elif file_extension in ['csv', 'xlsx', 'xls']:
            return process_spreadsheet_file(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    except Exception as e:
        current_app.logger.error(f"Error in process_file: {str(e)}")
        raise

def process_pdf_file(file_path):
    """Process a PDF file and extract transactions"""
    try:
        transactions = []
        
        # Use pdfplumber for better text extraction
        with pdfplumber.open(file_path) as pdf:
            current_app.logger.debug(f"Processing PDF with {len(pdf.pages)} pages")
            
            for page_num, page in enumerate(pdf.pages):
                # Extract text with better formatting preservation
                text = page.extract_text()
                current_app.logger.debug(f"Extracted text from page {page_num + 1}")
                current_app.logger.debug(f"Sample text: {text[:200]}...")  # Log sample for debugging
                
                # Extract transactions from the text
                page_transactions = extract_transactions_from_text(text)
                transactions.extend(page_transactions)
                current_app.logger.debug(f"Found {len(page_transactions)} transactions on page {page_num + 1}")
        
        current_app.logger.info(f"Successfully extracted {len(transactions)} transactions")
        
        return {
            'status': 'success',
            'transactions': transactions,
            'total_count': len(transactions)
        }
        
    except Exception as e:
        current_app.logger.error(f"Error processing PDF: {str(e)}")
        raise

def extract_transactions_from_text(text):
    """Extract transaction data from text using regex patterns"""
    transactions = []
    current_date = None
    
    # Multiple date patterns to handle different formats
    date_patterns = [
        r'Date Updated\s+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2})'
    ]
    
    # Transaction patterns with named groups
    transaction_patterns = [
        r'(?P<description>.*?)\s+US\$(?P<amount>[\d,]+\.\d{2})',
        r'(?P<description>.*?)\s+\$(?P<amount>[\d,]+\.\d{2})',
        r'(?P<description>.*?)\s+(?P<amount>[\d,]+\.\d{2})'
    ]

    # Extract date
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            try:
                for date_format in ['%B %d, %Y', '%d/%m/%Y', '%Y-%m-%d']:
                    try:
                        current_date = datetime.strptime(date_match.group(1), date_format)
                        break
                    except ValueError:
                        continue
                if current_date:
                    break
            except Exception as e:
                current_app.logger.warning(f"Date parsing error: {str(e)}")
                continue

    if not current_date:
        current_date = datetime.now()

    # Process each line
    for line in text.split('\n'):
        try:
            line = line.strip()
            
            # Skip header lines and empty lines
            if not line or any(header in line.lower() for header in 
                ['month', 'date updated', 'bill type', 'door', 'avenue', 'total']):
                continue
            
            # Try each transaction pattern
            for pattern in transaction_patterns:
                match = re.search(pattern, line)
                if match:
                    description = match.group('description').strip()
                    amount_str = match.group('amount').replace(',', '')
                    amount = Decimal(amount_str)
                    
                    # Classify the transaction
                    classification = classify_transaction(description, amount)
                    
                    # Determine debit/credit based on classification
                    # Following accounting principles:
                    # Debit: Assets+, Expenses+
                    # Credit: Liabilities+, Equity+, Revenue+
                    if classification['main_category'] in ['Assets', 'Expenses']:
                        debit_amount = amount
                        credit_amount = 0
                    elif classification['main_category'] in ['Liabilities', 'Equity', 'Revenue']:
                        debit_amount = 0
                        credit_amount = amount
                    
                    transaction = {
                        'transaction_date': current_date.strftime('%Y-%m-%d'),
                        'description': description,
                        'debit_amount': debit_amount,
                        'credit_amount': credit_amount,
                        'main_category': classification['main_category'],
                        'sub_category': classification['sub_category'],
                        'account': classification['account'],
                        'is_reconciled': False
                    }
                    
                    transactions.append(transaction)
                    current_app.logger.debug(f"Extracted transaction: {transaction}")
                    break
                    
        except Exception as e:
            current_app.logger.warning(f"Error processing line: {line}. Error: {str(e)}")
            continue
    
    return transactions

def process_spreadsheet_file(file_path):
    """Process a spreadsheet file and extract transactions"""
    try:
        # Add your spreadsheet processing logic here
        # Return extracted data
        return {'status': 'success', 'message': 'Spreadsheet processed'}
    except Exception as e:
        current_app.logger.error(f"Error processing spreadsheet: {str(e)}")
        raise

# Keywords for transaction classification
TRANSACTION_KEYWORDS = {
    # Asset related keywords
    'CURRENT_ASSETS': {
        'keywords': ['receivable', 'prepaid', 'insurance premium'],
        'mapping': ('Assets', 'Current Assets')
    },
    'NON_CURRENT_ASSETS': {
        'keywords': ['equipment', 'property purchase', 'improvement', 'furniture'],
        'mapping': ('Assets', 'Non-Current Assets')
    },
    
    # Liability related keywords
    'CURRENT_LIABILITIES': {
        'keywords': ['payable', 'unearned', 'deferred', 'deposit'],
        'mapping': ('Liabilities', 'Current Liabilities')
    },
    'NON_CURRENT_LIABILITIES': {
        'keywords': ['mortgage', 'long-term', 'loan'],
        'mapping': ('Liabilities', 'Non-Current Liabilities (Long-Term Debt)')
    },
    
    # Revenue related keywords
    'RENTAL_INCOME': {
        'keywords': ['rent payment', 'lease payment', 'rental income'],
        'mapping': ('Revenue', 'Rental Income')
    },
    'OTHER_REVENUE': {
        'keywords': ['parking fee', 'pet rent', 'application fee', 'late fee'],
        'mapping': ('Revenue', 'Other Revenue')
    },
    
    # Expense related keywords
    'ADMINISTRATIVE': {
        'keywords': ['admin', 'office supplies', 'management fee'],
        'mapping': ('Expenses', 'Operating Expenses (Administrative)')
    },
    'INSURANCE': {
        'keywords': ['insurance', 'coverage', 'policy'],
        'mapping': ('Expenses', 'Operating Expenses (Insurance)')
    },
    'PROFESSIONAL_FEES': {
        'keywords': ['legal', 'attorney', 'accounting', 'professional'],
        'mapping': ('Expenses', 'Operating Expenses (Professional Fees)')
    },
    'REPAIRS_MAINTENANCE': {
        'keywords': ['repair', 'maintenance', 'pest control', 'hvac', 'elevator'],
        'mapping': ('Expenses', 'Operating Expenses (Repairs and Maintenance)')
    },
    'MARKETING': {
        'keywords': ['advertising', 'marketing', 'promotion', 'signage'],
        'mapping': ('Expenses', 'Operating Expenses (Marketing)')
    },
    'PROPERTY_TAXES': {
        'keywords': ['property tax', 'tax assessment', 'real estate tax'],
        'mapping': ('Expenses', 'Operating Expenses (Property Taxes)')
    },
    'SECURITY': {
        'keywords': ['security', 'guard', 'surveillance', 'alarm'],
        'mapping': ('Expenses', 'Operating Expenses (Security)')
    },
    'UTILITIES': {
        'keywords': ['utility', 'electric', 'water', 'gas', 'waste'],
        'mapping': ('Expenses', 'Operating Expenses (Utilities)')
    },
    'COMMON_AREA': {
        'keywords': ['common area', 'cam', 'landscaping', 'cleaning'],
        'mapping': ('Expenses', 'Operating Expenses (Common Area)')
    },
    'FINANCIAL': {
        'keywords': ['bank fee', 'interest', 'processing fee', 'late fee'],
        'mapping': ('Expenses', 'Financial Expenses')
    },
    'LEVIES': {
        'keywords': ['levies', 'levy', 'hoa dues', 'hoa fee'],
        'mapping': ('Revenue', 'Rental Income')
    },
    'MAINTENANCE': {
        'keywords': ['maintenance', 'repairs', 'fixing'],
        'mapping': ('Expenses', 'Operating Expenses (Repairs and Maintenance)')
    },
    'SECURITY': {
        'keywords': ['security', 'guard', 'surveillance'],
        'mapping': ('Expenses', 'Operating Expenses (Security)')
    },
    'PROPERTY_MANAGEMENT': {
        'keywords': ['property management fee', 'management fee', 'property manager'],
        'mapping': ('Expenses', 'Operating Expenses (Professional Fees)')
    },
    'RESERVE_FUND': {
        'keywords': ['reserve fund', 'reserves'],
        'mapping': ('Liabilities', 'Current Liabilities')
    },
    'SPECIAL_ASSESSMENT': {
        'keywords': ['special assessment', 'special levy'],
        'mapping': ('Revenue', 'Other Revenue')
    },
    'AMENITIES': {
        'keywords': ['amenities', 'facility', 'common area'],
        'mapping': ('Expenses', 'Operating Expenses (Common Area)')
    },
    'INSURANCE': {
        'keywords': ['insurance', 'coverage'],
        'mapping': ('Expenses', 'Operating Expenses (Insurance)')
    },
    'OTHER_EXPENSES': {
        'keywords': ['other expense', 'miscellaneous'],
        'mapping': ('Expenses', 'Operating Expenses (Administrative)')
    }
}

def classify_transaction(description: str, amount: Decimal) -> Dict[str, str]:
    """Classify HOA transactions based on description and amount"""
    description = description.lower().strip()
    
    # Revenue Classifications
    if any(keyword in description for keyword in ['levies', 'levy', 'hoa fee', 'dues', 'assessment']):
        return {
            'main_category': 'Revenue',
            'sub_category': 'HOA Income',
            'account': 'HOA Fees'
        }
    
    # Equity Classifications (update this section)
    if any(keyword in description for keyword in ['reserve fund', 'reserves']):
        return {
            'main_category': 'Equity',
            'sub_category': 'Reserve Funds',
            'account': 'Reserve Fund'
        }
    
    # Asset Classifications
    if any(keyword in description for keyword in ['receivable', 'prepaid', 'advance']):
        return {
            'main_category': 'Assets',
            'sub_category': 'Current Assets',
            'account': 'Accounts Receivable'
        }
    
    # Expense Classifications
    if any(keyword in description for keyword in [
        'maintenance', 'repair', 'staff cost', 'salary', 'insurance',
        'management fee', 'utilities', 'security'
    ]):
        return {
            'main_category': 'Expenses',
            'sub_category': determine_expense_subcategory(description),
            'account': determine_expense_account(description)
        }
    
    # Default classification
    return {
        'main_category': 'Expenses',
        'sub_category': 'Operating Expenses (Administrative)',
        'account': 'Administrative Expenses'
    }

def determine_expense_subcategory(description: str) -> str:
    """Determine the expense subcategory based on the description"""
    description = description.lower()
    for category, info in TRANSACTION_KEYWORDS.items():
        if any(keyword in description for keyword in info['keywords']):
            return info['mapping'][1]
    return 'Operating Expenses (Administrative)'

def determine_expense_account(description: str) -> str:
    """Determine the specific expense account based on the description"""
    description = description.lower()
    for category, info in TRANSACTION_KEYWORDS.items():
        if any(keyword in description for keyword in info['keywords']):
            return info['mapping'][0]
    return 'Administrative Expenses'

def determine_account(main_category: str, sub_category: str, description: str) -> str:
    """Determine the specific account based on the classification"""
    # Get available accounts for the main category
    available_accounts = ACCOUNT_CLASSIFICATIONS.get(main_category, [])
    
    if isinstance(available_accounts, dict):  # Handle nested structure for Expenses
        available_accounts = [
            account
            for subcat in available_accounts.values()
            for account in (subcat if isinstance(subcat, list) else [subcat])
        ]
    
    # Try to match description with available accounts
    description = description.lower()
    for account in available_accounts:
        if any(word in description for word in account.lower().split()):
            return account
            
    # Return default account based on sub_category
    if main_category == 'Expenses':
        return 'Administrative Expenses'  # Default expense account
    elif main_category == 'Revenue':
        return 'Other Revenue'  # Default revenue account
    elif main_category == 'Assets':
        return 'Accounts Receivable'  # Default asset account
    elif main_category == 'Liabilities':
        return 'Accounts Payable'  # Default liability account
    else:
        return 'General Account'

def parse_transactions(text):
    transactions = []
    # Example regex pattern to match transaction lines
    transaction_pattern = re.compile(r'(?P<description>.+?)\s+US\$(?P<amount>\d+\.\d{2})')
    
    for line in text.splitlines():
        match = transaction_pattern.search(line)
        if match:
            transactions.append({
                'description': match.group('description').strip(),
                'amount': float(match.group('amount'))
            })
    
    return transactions

def extract_transactions_from_pdf(file_path):
    transactions = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            transactions.extend(parse_transactions(text))
    return transactions

def calculate_confidence_score(description: str) -> float:
    """Calculate confidence score based on classification certainty"""
    # Simple scoring based on keyword matches
    score = 0.5  # Base score
    description = description.lower()
    
    # Check for strong keywords
    for category_info in TRANSACTION_KEYWORDS.values():
        if any(keyword in description for keyword in category_info['keywords']):
            score += 0.3
            break
    
    # Add additional scoring factors
    if re.search(r'\d+', description):  # Contains numbers
        score += 0.1
    if len(description.split()) >= 3:  # Detailed description
        score += 0.1
        
    return min(score, 1.0)  # Cap at 1.0

def generate_reference_number() -> str:
    """Generate a unique reference number for the transaction"""
    return f"TX-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

def save_transactions_to_db(transactions_data):
    """Save extracted transactions to database"""
    saved_transactions = []
    try:
        for trans_data in transactions_data:
            transaction = Transaction(**trans_data)
            db.session.add(transaction)
            saved_transactions.append(transaction)
            
        db.session.commit()
        return saved_transactions
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving transactions: {str(e)}")
        raise

@transaction_routes.route('/transactions')
@login_required
def list_transactions():
    form = TransactionFilterForm()
    # Set property choices
    form.property_id.choices = [(p.id, p.name) for p in properties]
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Build query with filters
    query = Transaction.query
    
    # Date filters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if date_from:
        query = query.filter(Transaction.date >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Transaction.date <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    # Property filter
    property_id = request.args.get('property_id')
    if property_id:
        query = query.filter(Transaction.property_id == property_id)
    
    # Category filter
    category = request.args.get('category')
    if category:
        query = query.filter(Transaction.account == category)
    
    # Sorting
    sort_field = request.args.get('sort', 'date')
    sort_order = request.args.get('order', 'desc')
    
    if sort_field == 'date':
        query = query.order_by(Transaction.date.desc() if sort_order == 'desc' else Transaction.date.asc())
    elif sort_field in ['debit', 'credit']:
        sort_column = getattr(Transaction, f'{sort_field}_amount')
        query = query.order_by(sort_column.desc() if sort_order == 'desc' else sort_column.asc())
    
    # Execute paginated query
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get list of properties
    properties = Property.query.all()
    
    # Define account classifications (if not already defined at module level)
    account_classifications = {
        "Assets": ["Cash", "Accounts Receivable", "Prepaid Expenses", "Real Estate Properties", "Equipment"],
        "Liabilities": ["Accounts Payable", "Unearned Revenue", "Mortgage Payable", "Accrued Expenses"],
        "Equity": ["Owner's Capital", "Retained Earnings", "Common Stock"],
        "Revenue": ["Rental Income", "Parking Fees", "Maintenance Fee Income"],
        "Expenses": ["Property Taxes", "Utilities", "Insurance", "Maintenance and Repairs"]
    }
    
    # Pass it to both templates
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('transaction/_transactions_table.html',
                             transactions=pagination.items,
                             account_classifications=account_classifications)
    
    return render_template('transaction/transaction.html',
                         transactions=pagination.items,
                         properties=properties,
                         page=page,
                         total_pages=pagination.pages,
                         has_prev=pagination.has_prev,
                         has_next=pagination.has_next,
                         account_classifications=account_classifications,
                         today=datetime.today())

@transaction_routes.route('/transactions/<int:transaction_id>', methods=['PUT'])
@transaction_routes.route('/api/transactions/<int:transaction_id>', methods=['PUT'])  # Legacy support
@login_required
def update_transaction(transaction_id):
    try:
        data = request.json
        transaction = Transaction.query.get_or_404(transaction_id)
        
        # Verify user has permission to update this transaction
        if transaction.owner_id != Owner.query.filter_by(user_id=current_user.id).first().id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Update transaction fields if provided
        if 'transaction_date' in data:
            try:
                transaction.transaction_date = datetime.strptime(data['transaction_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format'}), 400

        if 'property_id' in data:
            # Verify property exists and belongs to user
            property_exists = Property.query.filter_by(
                id=data['property_id'], 
                owner_id=Owner.query.filter_by(user_id=current_user.id).first().id
            ).first()
            if not property_exists and data['property_id'] != 'portfolio':
                return jsonify({'error': 'Invalid property'}), 400
            transaction.property_id = data['property_id']

        # Update other fields
        if 'account' in data:
            transaction.account = data['account']
        if 'description' in data:
            transaction.description = data['description']
        if 'debit_amount' in data:
            transaction.debit_amount = float(data['debit_amount'])
        if 'credit_amount' in data:
            transaction.credit_amount = float(data['credit_amount'])
        if 'is_reconciled' in data:
            transaction.is_reconciled = bool(data['is_reconciled'])

        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Transaction updated successfully',
            'transaction': {
                'id': transaction.id,
                'transaction_date': transaction.transaction_date.strftime('%Y-%m-%d'),
                'property_id': transaction.property_id,
                'account': transaction.account,
                'description': transaction.description,
                'debit_amount': float(transaction.debit_amount) if transaction.debit_amount else 0.0,
                'credit_amount': float(transaction.credit_amount) if transaction.credit_amount else 0.0,
                'is_reconciled': transaction.is_reconciled
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@transaction_routes.route('/transactions/save_all', methods=['POST'])
@login_required
def save_all_transactions():
    try:
        transactions_data = request.form.getlist('transactions')
        
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            flash('Permission denied: Owner not found', 'error')
            return redirect(url_for('transaction_routes.portfolio_transactions'))
        
        for trans_data in transactions_data:
            transaction = Transaction.query.get(trans_data['id'])
            if transaction and transaction.owner_id == owner.id:
                transaction.transaction_date = datetime.strptime(trans_data['transaction_date'], '%Y-%m-%d')
                transaction.property_id = trans_data['property_id']
                transaction.account = trans_data['account']
                transaction.description = trans_data['description']
                transaction.debit_amount = Decimal(trans_data['debit_amount'])
                transaction.credit_amount = Decimal(trans_data['credit_amount'])
                transaction.is_reconciled = 'is_reconciled' in trans_data
        
        db.session.commit()
        flash('All transactions saved successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving all transactions: {str(e)}")
        flash(f'Failed to save all transactions: {str(e)}', 'error')
    
    return redirect(url_for('transaction_routes.portfolio_transactions'))


@transaction_routes.route('/portfolio/transactions', methods=['GET'])
@login_required
def portfolio_transactions():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            logger.error(f"Owner not found for user_id: {current_user.id}")
            flash('Owner account not found', 'error')
            return render_template('transaction/portfolio_transactions.html', 
                                transactions=[],
                                pagination={'pages': 0, 'page': 1},
                                properties=[],
                                form=TransactionForm(),
                                summary={'total_income': 0, 'total_expenses': 0, 'net_cash_flow': 0},
                                account_classifications={},
                                today=datetime.today(),
                                title='Portfolio Transactions',
                                error='Owner account not found')

        total_income = db.session.query(func.sum(Transaction.credit_amount))\
            .filter(Transaction.owner_id == owner.id).scalar() or 0
        
        total_expenses = db.session.query(func.sum(Transaction.debit_amount))\
            .filter(Transaction.owner_id == owner.id).scalar() or 0
        
        net_cash_flow = total_income - total_expenses

        summary = {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_cash_flow': net_cash_flow
        }

        account_classifications = {
            "Assets": ["Cash", "Accounts Receivable", "Prepaid Expenses", "Real Estate Properties", "Equipment"],
            "Liabilities": ["Accounts Payable", "Unearned Revenue", "Mortgage Payable", "Accrued Expenses"],
            "Equity": ["Owner's Capital", "Retained Earnings", "Common Stock"],
            "Revenue": ["Rental Income", "Parking Fees", "Maintenance Fee Income"],
            "Expenses": ["Property Taxes", "Utilities", "Insurance", "Maintenance and Repairs"]
        }

        query = Transaction.query.filter_by(owner_id=owner.id)
        
        if not request.args.get('include_reconciled', '').lower() == 'true':
            query = query.filter(Transaction.is_reconciled == False)

        pagination = query.order_by(Transaction.transaction_date.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )

        properties = Property.query.filter_by(owner_id=owner.id).all()
        properties_data = [{
            'id': p.id,
            'title': p.title,
            'description': p.description,
        } for p in properties]

        form = TransactionForm()
        property_choices = [
            ('portfolio', 'Portfolio (Fixed Amount)'), 
            ('all', 'All Properties (Split Equally)')
        ] + [(str(p.id), p.title) for p in properties]
        form.property_id.choices = property_choices

        template_data = {
            'transactions': pagination.items if pagination else [],
            'pagination': pagination if pagination else {'pages': 0, 'page': 1},
            'properties': properties_data,
            'form': form,
            'summary': summary,
            'account_classifications': account_classifications,
            'today': datetime.today(),
            'title': 'Portfolio Transactions'
        }

        return render_template('transaction/portfolio_transactions.html', **template_data)

    except Exception as e:
        logger.error(f"Error in portfolio_transactions: {str(e)}")
        flash('An error occurred while loading transactions', 'error')
        return render_template('transaction/portfolio_transactions.html', 
                            transactions=[],
                            pagination={'pages': 0, 'page': 1},
                            properties=[],
                            form=TransactionForm(),
                            summary={'total_income': 0, 'total_expenses': 0, 'net_cash_flow': 0},
                            account_classifications={},
                            today=datetime.today(),
                            title='Portfolio Transactions',
                            error='An error occurred while loading transactions')

@transaction_routes.route('/portfolio/transactions/create', methods=['POST'])
@login_required
def create_portfolio_transaction():
    form = TransactionForm()
    
    # Set form choices (required for validation)
    properties = Property.query.filter_by(owner_id=Owner.query.filter_by(user_id=current_user.id).first().id).all()
    form.property_id.choices = [('portfolio', 'Portfolio'), ('all', 'All Properties')] + \
                              [(str(p.id), p.title) for p in properties]
    
    account_choices = []
    for category, accounts in ACCOUNT_CLASSIFICATIONS.items():
        for account in accounts:
            account_choices.append((account, account))
    form.account.choices = account_choices

    if form.validate_on_submit():
        try:
            owner = Owner.query.filter_by(user_id=current_user.id).first()
            
            transaction = Transaction(
                transaction_date=form.transaction_date.data,
                property_id=None if form.property_id.data in ['portfolio', 'all'] else int(form.property_id.data),
                account=form.account.data,
                description=form.description.data,
                debit_amount=form.debit_amount.data,
                credit_amount=form.credit_amount.data,
                is_reconciled=form.is_reconciled.data,
                owner_id=owner.id,
                is_portfolio=form.property_id.data == 'portfolio'
            )
            
            db.session.add(transaction)
            
            # If "all properties" is selected, create split transactions
            if form.property_id.data == 'all':
                amount = form.debit_amount.data or form.credit_amount.data
                properties = Property.query.filter_by(owner_id=owner.id).all()
                split_amount = amount / len(properties)
                
                for property in properties:
                    split_transaction = Transaction(
                        transaction_date=form.transaction_date.data,
                        property_id=property.id,
                        account=form.account.data,
                        description=f"{form.description.data} (Split)",
                        debit_amount=split_amount if form.debit_amount.data else None,
                        credit_amount=split_amount if form.credit_amount.data else None,
                        is_reconciled=form.is_reconciled.data,
                        owner_id=owner.id
                    )
                    db.session.add(split_transaction)
            
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Transaction created successfully'})
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating transaction: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 400
    
    return jsonify({'status': 'error', 'message': 'Invalid form data', 'errors': form.errors}), 400

@transaction_routes.route('/transactions', methods=['POST'])
@login_required
def create_transaction():
    try:
        form = TransactionForm()
        form.property_id.choices = [(p.id, p.name) for p in properties]
        if form.validate_on_submit():
            # Create transaction using form data
            transaction = Transaction(
                transaction_date=form.date.data,
                property_id=form.property_id.data,
                main_category=form.main_category.data,
                sub_category=form.sub_category.data,
                account=form.account.data,
                description=form.description.data,
                debit_amount=form.amount.data,
                owner_id=Owner.query.filter_by(user_id=current_user.id).first().id
            )
            db.session.add(transaction)
            db.session.commit()
            return jsonify({
                'id': transaction.id,
                'message': 'Transaction created successfully'
            })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@transaction_routes.route('/transactions/<int:id>', methods=['PUT'])
@transaction_routes.route('/api/transactions/<int:id>', methods=['PUT'])  # Legacy support
def update_transaction_api(id):
    try:
        transaction = Transaction.query.get_or_404(id)
        data = request.json
        
        # Verify ownership
        if transaction.property.owner_id != Owner.query.filter_by(user_id=current_user.id).first().id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Don't allow editing reconciled transactions
        if transaction.is_reconciled:
            return jsonify({'error': 'Cannot edit reconciled transactions'}), 400
        
        transaction.transaction_date = datetime.strptime(data['date'], '%Y-%m-%d')
        transaction.property_id = data['property_id']
        transaction.main_category = data['category']
        transaction.account = data['account']
        transaction.description = data['description']
        transaction.debit_amount = Decimal(data['amount'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@transaction_routes.route('/transactions/<int:transaction_id>/update', methods=['PUT'])
@transaction_routes.route('/api/transactions/<int:transaction_id>/update', methods=['PUT'])  # Legacy support
def update_transaction_alt(transaction_id):
    try:
        transaction = Transaction.query.get_or_404(transaction_id)
        data = request.json
        
        # Verify ownership
        if transaction.property.owner_id != Owner.query.filter_by(user_id=current_user.id).first().id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Don't allow editing reconciled transactions
        if transaction.is_reconciled:
            return jsonify({'error': 'Cannot edit reconciled transactions'}), 400
        
        transaction.transaction_date = datetime.strptime(data['date'], '%Y-%m-%d')
        transaction.property_id = data['property_id']
        transaction.main_category = data['category']
        transaction.account = data['account']
        transaction.description = data['description']
        transaction.debit_amount = Decimal(data['amount'])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@transaction_routes.route('/transactions/<int:transaction_id>/split', methods=['POST'])
@transaction_routes.route('/api/transactions/<int:transaction_id>/split', methods=['POST'])  # Legacy support
@login_required
def split_transaction(transaction_id):
    try:
        transaction = Transaction.query.get_or_404(transaction_id)
        
        # Verify ownership
        if transaction.property.owner_id != Owner.query.filter_by(user_id=current_user.id).first().id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get all properties for the owner
        properties = Property.query.filter_by(owner_id=transaction.property.owner_id).all()
        
        # Calculate split amount
        amount = transaction.debit_amount or transaction.credit_amount
        split_amount = amount / len(properties)
        
        # Create new transactions for each property
        new_transactions = []
        for property in properties:
            new_transaction = Transaction(
                transaction_date=transaction.transaction_date,
                property_id=property.id,
                main_category=transaction.main_category,
                account=transaction.account,
                description=f"{transaction.description} (Split)",
                debit_amount=split_amount if transaction.debit_amount else None,
                credit_amount=split_amount if transaction.credit_amount else None,
                owner_id=transaction.owner_id
            )
            new_transactions.append(new_transaction)
        
        # Delete original transaction
        db.session.delete(transaction)
        
        # Add new transactions
        db.session.add_all(new_transactions)
        db.session.commit()
        
        return jsonify({'message': 'Transaction split successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@transaction_routes.route('/transactions/<int:transaction_id>/portfolio', methods=['POST'])
@transaction_routes.route('/api/transactions/<int:transaction_id>/portfolio', methods=['POST'])  # Legacy support
@login_required
def mark_portfolio_transaction(transaction_id):
    try:
        transaction = Transaction.query.get_or_404(transaction_id)
        
        # Verify ownership
        if transaction.property.owner_id != Owner.query.filter_by(user_id=current_user.id).first().id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Mark as portfolio transaction
        transaction.is_portfolio = True
        transaction.property_id = None  # Or set to a special portfolio property ID
        
        db.session.commit()
        return jsonify({'message': 'Transaction marked as portfolio successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

def handle_transaction_error(func):
    """Decorator for handling transaction-related errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in {func.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Database error occurred'
            }), 500
        except TransactionError as e:
            logger.error(f"Transaction error in {func.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'An unexpected error occurred'
            }), 500
    return wrapper

def cleanup_temp_file(filepath):
    """Remove temporary file after processing"""
    if os.path.exists(filepath):
        os.remove(filepath)

def save_transactions(transactions, user_id):
    """Save extracted transactions to database"""
    try:
        owner = Owner.query.filter_by(user_id=user_id).first()
        if not owner:
            raise ValueError("Owner not found")
            
        for trans_data in transactions:
            transaction = Transaction(
                transaction_date=datetime.strptime(trans_data['date'], '%Y-%m-%d'),
                description=trans_data.get('description', ''),
                debit_amount=trans_data.get('debit_amount', 0),
                credit_amount=trans_data.get('credit_amount', 0),
                owner_id=owner.id,
                is_portfolio=True
            )
            db.session.add(transaction)
        
        db.session.commit()
        current_app.logger.info(f"Saved {len(transactions)} transactions to database")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving transactions: {str(e)}")
        raise

def safe_date_str(date):
    """Safely convert datetime to string, handling None values"""
    return date.strftime('%Y-%m-%d') if date else ''

@transaction_routes.route('/transactions/save', methods=['POST'])
@login_required
def save_transactions():
    form = TransactionForm()
    
    if form.validate_on_submit():
        try:
            # Get owner associated with current user
            owner = Owner.query.filter_by(user_id=current_user.id).first()
            if not owner:
                flash('Owner not found', 'error')
                return redirect(url_for('transaction_routes.list_transactions'))
            
            new_transaction = Transaction(
                transaction_date=form.transaction_date.data,
                description=form.description.data,
                debit_amount=form.debit_amount.data or None,
                credit_amount=form.credit_amount.data or None,
                account=form.account.data,
                is_reconciled=form.is_reconciled.data,
                owner_id=owner.id,
                property_id=form.property_id.data
            )
            
            db.session.add(new_transaction)
            db.session.commit()
            
            flash('Transaction saved successfully', 'success')
            return redirect(url_for('transaction_routes.list_transactions'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving transaction: {str(e)}")
            flash(f'Error saving transaction: {str(e)}', 'error')
            return redirect(url_for('transaction_routes.list_transactions'))
    
    # If form validation failed
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('transaction_routes.list_transactions'))

@transaction_routes.route('/update_transaction/<int:transaction_id>', methods=['POST'])
@transaction_routes.route('/api/update_transaction/<int:transaction_id>', methods=['POST'])  # Legacy support
@login_required
def update_transaction_form(transaction_id):
    form = TransactionForm()
    
    if form.validate_on_submit():
        try:
            # Get the transaction
            transaction = Transaction.query.get_or_404(transaction_id)
            
            # Get owner and verify permissions
            owner = Owner.query.filter_by(user_id=current_user.id).first()
            if not owner or transaction.owner_id != owner.id:
                flash('Permission denied', 'error')
                return redirect(url_for('transaction_routes.list_transactions'))

            # Update transaction with form data
            transaction.transaction_date = form.transaction_date.data
            transaction.property_id = form.property_id.data
            transaction.account = form.account.data
            transaction.description = form.description.data
            transaction.debit_amount = form.debit_amount.data
            transaction.credit_amount = form.credit_amount.data
            transaction.is_reconciled = form.is_reconciled.data
            
            db.session.commit()
            flash('Transaction updated successfully', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating transaction {transaction_id}: {str(e)}")
            flash(f'Error updating transaction: {str(e)}', 'error')
    else:
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('transaction_routes.list_transactions'))

@transaction_routes.route('/monthly-financials')
@login_required
def monthly_financials():
    try:
        # Get current year
        current_year = datetime.now().year
        
        # Get owner's transactions
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Base query for owner's transactions in current year
        base_query = Transaction.query.filter(
            Transaction.owner_id == owner.id,
            extract('year', Transaction.transaction_date) == current_year
        )

        # Initialize monthly data
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        monthly_income = [0] * 12
        monthly_expenses = [0] * 12
        monthly_cashflow = [0] * 12

        # Get monthly income (credits)
        income_results = db.session.query(
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(Transaction.credit_amount).label('total')
        ).filter(
            Transaction.owner_id == owner.id,
            Transaction.credit_amount > 0,
            extract('year', Transaction.transaction_date) == current_year
        ).group_by(
            extract('month', Transaction.transaction_date)
        ).all()

        # Get monthly expenses (debits)
        expense_results = db.session.query(
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(Transaction.debit_amount).label('total')
        ).filter(
            Transaction.owner_id == owner.id,
            Transaction.debit_amount > 0,
            extract('year', Transaction.transaction_date) == current_year
        ).group_by(
            extract('month', Transaction.transaction_date)
        ).all()

        # Populate monthly arrays
        for month, total in income_results:
            monthly_income[int(month) - 1] = float(total or 0)

        for month, total in expense_results:
            monthly_expenses[int(month) - 1] = float(total or 0)

        # Calculate monthly cashflow
        for i in range(12):
            monthly_cashflow[i] = monthly_income[i] - monthly_expenses[i]

        data = {
            'months': months,
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'monthly_cashflow': monthly_cashflow
        }

        return jsonify(data)

    except Exception as e:
        current_app.logger.error(f"Error in monthly_financials: {str(e)}")
        return jsonify({'error': 'Failed to fetch monthly financials'}), 500

@transaction_routes.route('/financial-data/<period>')
def get_financial_data(period):
    # Get current date
    today = datetime.now()
    
    # Define date ranges based on period
    if period == 'today':
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'month':
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today
    elif period == 'year':
        start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today
    elif period == 'custom':
        # Handle custom date range if needed
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if not start_date or not end_date:
            return jsonify({'error': 'Start and end dates required for custom range'}), 400
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        return jsonify({'error': 'Invalid period'}), 400
    
    # Add owner filter if user is logged in
    query = db.session.query(
        func.sum(Transaction.debit_amount).label('total_debit'),
        func.sum(Transaction.credit_amount).label('total_credit'),
        func.date_trunc('day', Transaction.transaction_date).label('date')
    ).filter(
        Transaction.transaction_date.between(start_date, end_date)
    )
    
    if current_user.is_authenticated:
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if owner:
            query = query.filter(Transaction.owner_id == owner.id)
    
    # Group and order the results
    transactions = query.group_by(
        func.date_trunc('day', Transaction.transaction_date)
    ).order_by(
        func.date_trunc('day', Transaction.transaction_date)
    ).all()
    
    # Process the data for the chart
    dates = []
    income_data = []
    expenses_data = []
    
    for t in transactions:
        dates.append(t.date.strftime('%Y-%m-%d'))
        income_data.append(float(t.total_debit or 0))
        expenses_data.append(float(t.total_credit or 0))
    
    return jsonify({
        'dates': dates,
        'income': income_data,
        'expenses': expenses_data,
        'period': period
    })

@transaction_routes.route('/expenses-data')
@login_required
def get_expenses_data():
    try:
        current_year = datetime.utcnow().year
        
        # Get owner and associated user's currency
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            current_app.logger.warning(f"Owner not found for user {current_user.id}")
            return jsonify({'error': 'Owner not found'}), 404

        # Get user's currency
        user = User.query.get(current_user.id)
        if not user or not user.currency_id:
            current_app.logger.warning(f"Currency not set for user {current_user.id}")
            currency_symbol = '$'  # Default fallback
        else:
            currency = Currency.query.get(user.currency_id)
            currency_symbol = currency.symbol if currency else '$'

        # Query expenses with better categorization
        expenses = db.session.query(
            Transaction.main_category,
            Transaction.sub_category,
            func.sum(Transaction.debit_amount).label('total_amount')
        ).filter(
            Transaction.owner_id == owner.id,
            Transaction.debit_amount > 0,
            extract('year', Transaction.transaction_date) == current_year
        ).group_by(
            Transaction.main_category,
            Transaction.sub_category
        ).order_by(
            func.sum(Transaction.debit_amount).desc()
        ).all()
        
        current_app.logger.debug(f"Found {len(expenses)} expense categories")

        # Process and format the data
        expense_data = {}
        for main_cat, sub_cat, amount in expenses:
            main_category = main_cat or 'Uncategorized'
            if main_category not in expense_data:
                expense_data[main_category] = 0
            expense_data[main_category] += float(amount or 0)

        # Sort by amount descending
        sorted_expenses = sorted(
            expense_data.items(), 
            key=lambda x: x[1], 
            reverse=True
        )

        response_data = {
            'labels': [item[0] for item in sorted_expenses],
            'series': [item[1] for item in sorted_expenses],
            'currencySymbol': currency_symbol,
            'total': sum(expense_data.values())
        }
        
        current_app.logger.debug(f"Returning expense data with {len(response_data['labels'])} categories")
        return jsonify(response_data)

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in get_expenses_data: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_expenses_data: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

def determine_expense_subcategory(description: str) -> str:
    """Determine expense subcategory based on description"""
    description = description.lower()
    
    subcategory_mapping = {
        'maintenance': ['repair', 'maintenance', 'fixing'],
        'utilities': ['electric', 'water', 'gas', 'utility'],
        'insurance': ['insurance', 'coverage'],
        'taxes': ['tax', 'levy', 'assessment'],
        'management': ['management fee', 'property manager'],
        'security': ['security', 'guard', 'surveillance'],
        'amenities': ['amenity', 'facility', 'common area']
    }

    for subcategory, keywords in subcategory_mapping.items():
        if any(keyword in description for keyword in keywords):
            return f"Operating Expenses ({subcategory.title()})"

    return "Operating Expenses (Administrative)"  # Default subcategory

def determine_expense_account(description: str) -> str:
    """Determine specific expense account based on transaction description"""
    description = description.lower()
    
    if any(word in description for word in ['maintenance', 'repair']):
        return 'Maintenance and Repairs'
    elif any(word in description for word in ['insurance', 'coverage']):
        return 'Insurance'
    elif any(word in description for word in ['utility', 'electric', 'water', 'gas']):
        return 'Utilities'
    elif any(word in description for word in ['management fee', 'professional']):
        return 'Professional Fees'
    elif any(word in description for word in ['security', 'guard']):
        return 'Security'
    else:
        return 'Administrative Expenses'  # Default expense account
    

@transaction_routes.route('/transactions/portfolio/transactions/<int:transaction_id>/update', methods=['PUT'])
@login_required
def update_portfolio_transaction(transaction_id):
    try:
        # Get the transaction and verify ownership
        transaction = Transaction.query.get_or_404(transaction_id)
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        
        if not owner or transaction.owner_id != owner.id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        # Get JSON data from request
        data = request.get_json()
        
        # Update transaction fields
        if 'transaction_date' in data:
            transaction.transaction_date = datetime.strptime(data['transaction_date'], '%Y-%m-%d')
        if 'property_id' in data:
            transaction.property_id = None if data['property_id'] == 'portfolio' else int(data['property_id'])
            transaction.is_portfolio = (data['property_id'] == 'portfolio')
        if 'account' in data:
            transaction.account = data['account']
        if 'description' in data:
            transaction.description = data['description']
        if 'debit_amount' in data:
            transaction.debit_amount = data['debit_amount']
        if 'credit_amount' in data:
            transaction.credit_amount = data['credit_amount']
        if 'is_reconciled' in data:
            transaction.is_reconciled = data['is_reconciled']
            
        db.session.commit()
        
        return jsonify({
            'message': 'Transaction updated successfully',
            'transaction': {
                'id': transaction.id,
                'transaction_date': transaction.transaction_date.strftime('%Y-%m-%d'),
                'property_id': 'portfolio' if transaction.is_portfolio else transaction.property_id,
                'account': transaction.account,
                'description': transaction.description,
                'debit_amount': float(transaction.debit_amount) if transaction.debit_amount else None,
                'credit_amount': float(transaction.credit_amount) if transaction.credit_amount else None,
                'is_reconciled': transaction.is_reconciled
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating transaction: {str(e)}")
        return jsonify({'error': str(e)}), 400

@transaction_routes.route('/save_portfolio_transactions', methods=['POST'])
@login_required
def save_portfolio_transactions():
    try:
        # Get owner associated with current user
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Get JSON data from request
        data = request.get_json()
        if not data or 'transactions' not in data:
            return jsonify({'error': 'No transaction data provided'}), 400

        saved_transactions = []
        properties = Property.query.filter_by(owner_id=owner.id).all()

        for trans_data in data['transactions']:
            if trans_data.get('property') == 'all':
                # Handle split transactions
                amount = trans_data.get('debit_amount') or trans_data.get('credit_amount')
                split_amount = amount / len(properties)
                
                for property in properties:
                    transaction = Transaction(
                        transaction_date=datetime.strptime(trans_data['transaction_date'], '%Y-%m-%d'),
                        property_id=property.id,
                        account=trans_data['account'],
                        description=f"{trans_data['description']} (Split)",
                        debit_amount=split_amount if trans_data.get('debit_amount') else None,
                        credit_amount=split_amount if trans_data.get('credit_amount') else None,
                        is_reconciled=trans_data.get('is_reconciled', False),
                        owner_id=owner.id
                    )
                    db.session.add(transaction)
                    saved_transactions.append(transaction)
            else:
                # Handle single transaction
                transaction = Transaction(
                    transaction_date=datetime.strptime(trans_data['transaction_date'], '%Y-%m-%d'),
                    property_id=None if trans_data['property'] == 'portfolio' else int(trans_data['property']),
                    account=trans_data['account'],
                    description=trans_data['description'],
                    debit_amount=trans_data.get('debit_amount'),
                    credit_amount=trans_data.get('credit_amount'),
                    is_reconciled=trans_data.get('is_reconciled', False),
                    owner_id=owner.id,
                    is_portfolio=trans_data['property'] == 'portfolio'
                )
                db.session.add(transaction)
                saved_transactions.append(transaction)

        db.session.commit()
        
        return jsonify({
            'message': 'Transactions saved successfully',
            'transactions': [{
                'id': t.id,
                'transaction_date': t.transaction_date.strftime('%Y-%m-%d'),
                'property_id': 'portfolio' if t.is_portfolio else t.property_id,
                'account': t.account,
                'description': t.description,
                'debit_amount': float(t.debit_amount) if t.debit_amount else None,
                'credit_amount': float(t.credit_amount) if t.credit_amount else None,
                'is_reconciled': t.is_reconciled
            } for t in saved_transactions]
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving transactions: {str(e)}")
        return jsonify({'error': str(e)}), 400

@transaction_routes.route('/portfolio_transactions')
@login_required
def portfolio_transactions():
    form = PortfolioTransactionsForm()
    
    # Get the current user's owner record
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    if not owner:
        flash('Owner not found', 'error')
        return redirect(url_for('main.dashboard'))

    # Fetch transactions for the current owner
    transactions = Transaction.query.filter_by(owner_id=owner.id).all()

    # Populate the form with existing transactions
    for transaction in transactions:
        form.transactions.append_entry({
            'date': transaction.transaction_date,
            'property': transaction.property_id or 'portfolio',
            'account': transaction.account,
            'description': transaction.description,
            'debit': transaction.debit_amount,
            'credit': transaction.credit_amount,
            'reconciled': transaction.is_reconciled
        })

    # Fetch properties and account classifications for filters
    properties = Property.query.filter_by(owner_id=owner.id).all()
    account_classifications = ACCOUNT_CLASSIFICATIONS

    return render_template(
        'transaction/portfolio_transactions.html',
        form=form,
        properties=properties,
        account_classifications=account_classifications,
        transactions=transactions
    )

@transaction_routes.route('/portfolio-transactions')
def portfolio_transactions():
    transactions = Transaction.query.all()  # Fetch transactions from the database
    return render_template('transaction/portfolio_transactions.html', transactions=transactions)
>>>>>>> origin/main
