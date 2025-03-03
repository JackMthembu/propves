from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, jsonify, abort
from flask_login import login_required, current_user
from models import Property, Owner, Photo, Listing, RentalAgreement, Photo, Country, State
from extensions import db
from forms import PropertyDetailsForm, FeatureForm, AddressForm, PhotoForm, ListingForm
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import shutil
from sqlalchemy.exc import SQLAlchemyError
from flask_wtf import FlaskForm
import traceback
from utils import allowed_file 

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
    return render_template('property/property_list.html', properties=properties_data, form=form, listing=None, rental_agreements=[])

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
    """Edit property details or create a new property if no property_id exists."""
    current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
    
    if not current_user_owner:
        flash('User is not registered as an owner.', 'error')
        return redirect(url_for('main.dashboard'))

    if property_id == 'new':
        property = Property(owner_id=current_user_owner.id)  
        form = PropertyDetailsForm()  
    else:
        property = Property.query.get_or_404(property_id)  
        if property.owner_id != current_user_owner.id:
            abort(403)  
        form = PropertyDetailsForm(obj=property)  

    if request.method == 'GET':
        if property_id != 'new':

            form.title.data = property.title
            form.type.data = property.type
            form.description.data = property.description
            form.bedroom.data = property.bedroom
            form.bathroom.data = property.bathroom
            form.kitchen.data = property.kitchen
            form.garage.data = property.garage
            form.sqm.data = property.sqm
            form.max_occupants.data = property.max_occupants

    if form.validate_on_submit():
        # Update or set property fields based on form data
        property.title = form.title.data
        property.type = form.type.data
        property.description = form.description.data
        property.bedroom = form.bedroom.data
        property.bathroom = form.bathroom.data
        property.kitchen = form.kitchen.data
        property.garage = form.garage.data
        property.sqm = form.sqm.data
        property.max_occupants = form.max_occupants.data

        try:
            if property_id == 'new':
                db.session.add(property)  
                db.session.commit()  
                flash('New property created successfully!', 'success')
                return redirect(url_for('property_routes.manage_property', property_id=property.id))  # Redirect to manage property
            else:
                db.session.commit()  
                flash('Property details updated successfully!', 'success')
                return redirect(url_for('property_routes.manage_property', property_id=property.id))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating property details: {str(e)}", exc_info=True)
            flash('Error updating property details. Please try again.', 'danger')
            return redirect(url_for('property_routes.manage_property', property_id=property.id))


    return render_template('property/edit_details.html', form=form, property=property)

@property_routes.route('/property/edit_features/<property_id>', methods=['GET', 'POST'])
@login_required
def edit_features(property_id):
    """Edit property features"""
    property = Property.query.get_or_404(property_id)

    current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
    
    if not current_user_owner or property.owner_id != current_user_owner.id:
        abort(403)

    form = FeatureForm()

    if request.method == 'GET':
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
        # Update property features based on form data
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
            db.session.commit()  # Commit changes to the database
            flash('Property features updated successfully!', 'success')
            return redirect(url_for('property_routes.manage_property', property_id=property.id))
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            current_app.logger.error(f"Error updating property features: {str(e)}")
            flash('Error updating property features. Please try again.', 'danger')

    return render_template('property/edit_features.html', property=property, form=form)

@property_routes.route('/property/edit_address/<int:property_id>', methods=['GET', 'POST'])
@login_required
def edit_address(property_id):
    try:
        current_app.logger.info(f"Starting edit_address for property_id: {property_id}")
        
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

@property_routes.route('/property/<int:property_id>/upload-photos', methods=['POST'])
@login_required
def upload_photos(property_id):
    current_app.logger.info(f"Upload photos called for property ID: {property_id}")
    
    if 'photos' not in request.files:
        flash('No file part', 'error')
        current_app.logger.error('No file part in request')
        return redirect(request.referrer)
    
    photos = request.files.getlist('photos')
    
    if not photos or all(photo.filename == '' for photo in photos):
        flash('No selected file', 'error')
        current_app.logger.error('No selected file')
        return redirect(request.referrer)

    try:
        property = Property.query.get_or_404(property_id)
        current_app.logger.info(f"Property found: {property.id}")

        # Check if there are existing thumbnails
        existing_photos = Photo.query.filter_by(property_id=property_id).all()
        has_thumbnail = any(photo.is_thumbnail for photo in existing_photos)

        for index, photo in enumerate(photos):
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                # Set the upload path to static/uploads/property_photos
                upload_folder = os.path.join(current_app.static_folder, 'uploads', 'property_photos')
                filepath = os.path.join(upload_folder, filename)
                
                # Log the file path before saving
                current_app.logger.info(f"Saving photo to: {filepath}")
                
                # Ensure the upload directory exists
                os.makedirs(upload_folder, exist_ok=True)
                
                # Save the photo
                photo.save(filepath)
                
                # Create photo record in database
                new_photo = Photo(
                    property_id=property_id,
                    file_path=os.path.join('uploads', 'property_photos', filename),
                    filename=filename,
                    is_thumbnail=False  # Set the uploaded photo's is_thumbnail to False
                )
                
                # If there are no existing thumbnails, set the first uploaded photo as thumbnail
                if not has_thumbnail and index == 0:
                    new_photo.is_thumbnail = True
                
                db.session.add(new_photo)
        
        db.session.commit()
        flash('Photos uploaded successfully', 'success')
        current_app.logger.info('Photos uploaded successfully')
    except Exception as e:
        current_app.logger.error(f"Error during photo upload: {str(e)}")
        db.session.rollback()  # Rollback the session in case of error
        flash('An error occurred while uploading photos', 'error')
    
    return redirect(request.referrer)


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

@property_routes.route('/property/delete_photos', methods=['POST'])
@login_required
def delete_photos():
    try:
        photo_ids = request.form.getlist('photo_ids')  # Get the list of photo IDs
        if not photo_ids:
            flash('No photos selected for deletion.', 'warning')
            return redirect(url_for('property_routes.manage_property', property_id=property.id))

        for photo_id in photo_ids:
            # Get the photo
            photo = Photo.query.get_or_404(photo_id)
            
            # Get the property
            property = Property.query.get_or_404(photo.property_id)
            
            # Verify ownership
            current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()
            if not current_user_owner or property.owner_id != current_user_owner.id:
                flash('You do not have permission to delete this photo.', 'error')
                return redirect(url_for('property_routes.manage_property', property_id=property.id))

            # Delete the photo file
            if photo.filename:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], photo.filename)
                if os.path.exists(file_path):
                    os.remove(file_path)

            # Delete from database
            db.session.delete(photo)

        db.session.commit()
        flash('Selected photos deleted successfully', 'success')
        return redirect(url_for('property_routes.manage_property', property_id=property.id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting photos: {str(e)}")
        flash('An error occurred while deleting the photos', 'error')
        return redirect(url_for('property_routes.manage_property', property_id=property.id))
