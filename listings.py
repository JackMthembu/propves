<<<<<<< HEAD
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, jsonify
from flask_login import login_required, current_user
from models import Property, Owner, Listing, RentalAgreement
from extensions import db
from forms import ListingForm
from datetime import datetime

listing_routes = Blueprint('listing_routes', __name__)

@listing_routes.route('/listing/create_listing/<int:property_id>', methods=['GET', 'POST'])
@login_required
def create_listing(property_id):
    property = Property.query.get_or_404(property_id)
    form = ListingForm()

    if request.method == 'GET':
        return render_template('listing/create_listing.html', property=property, form=form)

    if form.validate_on_submit():
        try:
            new_listing = Listing(
                property_id=property_id,
                deposit=form.deposit.data,
                admin_fee=form.admin_fee.data,
                listing_type=form.listing_type.data,
                monthly_rental=form.monthly_rental.data,
                available_start_date=form.available_start_date.data,
                available_end_date=form.available_end_date.data,
                viewing_availibility_dates=form.viewing_availibility_dates.data,
                status=1,
                date_created=datetime.utcnow()
            )
            db.session.add(new_listing)
            db.session.commit()
            return jsonify({"message": "Listing created successfully!"}), 201

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating listing: {str(e)}")
            return jsonify({"error": "An error occurred while creating the listing."}), 500

@listing_routes.route('/listing/toggle_listing_status/<int:listing_id>', methods=['POST'])
@login_required
def toggle_listing_status(listing_id):
    try:
        listing = Listing.query.get_or_404(listing_id)
        property = listing.property
        current_user_owner = Owner.query.filter_by(user_id=current_user.id).first()

        if not current_user_owner or property.owner_id != current_user_owner.id:
            abort(403)

        latest_agreement = RentalAgreement.query.filter_by(property_id=property.id).order_by(RentalAgreement.date_created.desc()).first()

        if latest_agreement and latest_agreement.status == 'accepted':
            listing.status = False
            db.session.commit()
        elif listing.status is True:
            if latest_agreement and latest_agreement.status == 'pending':
                listing_status = 'Pending'
            else:
                listing_status = 'Listed'
        else:
            listing_status = 'Unlisted'

        return redirect(url_for('listing_routes.property_list'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling listing status: {str(e)}")
        flash('Error updating listing status.', 'danger')
        return redirect(url_for('listing_routes.property_list'))

@listing_routes.route('/listing/edit_listing/<int:listing_id>', methods=['GET', 'POST'])
@login_required
def edit_listing(listing_id):
    listing = Listing.query.get(listing_id)
    if listing is None:
        return redirect(url_for('some_error_page'))

    property = listing.property
    form = ListingForm(obj=listing)

    if form.validate_on_submit():
        try:
            listing.deposit = form.deposit.data
            listing.admin_fee = form.admin_fee.data
            listing.listing_type = form.listing_type.data
            listing.monthly_rental = form.monthly_rental.data
            listing.available_start_date = form.available_start_date.data
            listing.available_end_date = form.available_end_date.data
            listing.viewing_availibility_dates = form.viewing_availibility_dates.data
            
            db.session.commit()
            flash('Listing updated successfully!', 'success')
            return redirect(url_for('property_routes.manage_property', property_id=property.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating listing: {str(e)}")
            flash('Error updating listing.', 'danger')

    return render_template('listing/edit_listing.html', listing=listing, property=property, form=form)
=======
from ast import main
from datetime import datetime
import math
import os
from geopy.distance import geodesic
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from googlemaps import Client as GoogleMaps
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename
from config import GOOGLE_MAPS_API_KEY
from extensions import db
from forms import ProfileForm, ProfilePicForm
from models import Calendar, Country, Listing, Photo, Property
from sqlalchemy.orm import sessionmaker

listing_routes = Blueprint('listing_routes', __name__)

engine = create_engine('mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server')
Session = sessionmaker(bind=engine)
db_session = Session() 

if not GOOGLE_MAPS_API_KEY:
    raise ValueError("No Google Maps API key found. Set the GOOGLE_MAPS_API_KEY environment variable.")

from googlemaps import Client as GoogleMaps

google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY') 

if not google_maps_api_key:
    raise ValueError("GOOGLE_MAPS_API_KEY is not set in environment variables.")

api_key = os.getenv('GOOGLE_MAPS_API_KEY')
if not api_key:
    raise ValueError("GOOGLE_MAPS_API_KEY is not set in environment variables.")
gmaps = GoogleMaps(api_key)

def get_coordinates(city):
    """Get latitude and longitude for a city using Google Maps API"""
    geocode_result = gmaps.geocode(city)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        return location['lat'], location['lng']
    return None

def calculate_distance(coord1, coord2):
    """Calculate distance between two coordinates using geopy"""
    return geodesic(coord1, coord2).kilometers

@listing_routes.route('/list_property/<int:property_id>', methods=['GET', 'POST'])
@login_required
def list_property(property_id):
    property = Property.query.get_or_404(property_id)

    if property.owner_id != current_user.owner_id and current_user.manager_id is None:
        abort(403)

    property_features = {
        "bedrooms": property.bedroom,
        "garage": property.garage,
        "kitchen": property.kitchen,
        "swimming_pool": property.swimming_pool,
        "garden": property.garden,
        "air_conditioning": property.air_conditioning,
        "heating": property.heating,
        "gym": property.gym,
        "laundry": property.laundry,
        "fireplace": property.fireplace,
        "balcony": property.balcony,
        "pet_friendly": property.pet_friendly,
        "bbq_area": property.bbq_area,
        "jacuzzi": property.jacuzzi,
        "tennis_court": property.tennis_court
    }

    suburb = property.suburb
    city = property.city
    state_id = property.state_id
    country_id = property.country_id

    photos = Photo.query.filter_by(property_id=property_id).all()

    if request.method == 'POST':
        deposit = request.form.get('deposit')
        monthly_rental = request.form.get('monthly_rental')
        available_start_date = request.form.get('available_start_date')
        available_end_date = request.form.get('available_end_date')

        if not all([deposit, monthly_rental, available_start_date]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('listing_routes.list_property', property_id=property_id))

        new_listing = Listing(
            deposit=deposit,
            monthly_rental=monthly_rental,
            available_start_date=available_start_date,
            available_end_date=available_end_date,
            property_id=property_id
        )
        db.session.add(new_listing)
        db.session.commit()

        flash('Property listed successfully!', 'success')
        return redirect(url_for('property_routes.property_list')) 

    return render_template('list_property.html', property=property, property_features=property_features, suburb=suburb, city=city, state_id=state_id, country_id=country_id, photos=photos)

# ========================================== Search

@listing_routes.route('/search', methods=['GET'])
def search_listings():
    city = request.args.get('city')
    if not city:
        return jsonify([])

    # Get coordinates for the search city
    city_coords = get_coordinates(city)
    if not city_coords:
        return jsonify([])

    # Get all listings
    listings = Listing.query.all()
    nearby_listings = []

    for listing in listings:
        property = listing.property
        if property.latitude and property.longitude:
            distance = calculate_distance(
                city_coords, 
                (property.latitude, property.longitude)
            )
            # Add listings within 10km
            if distance <= 10:
                nearby_listings.append({
                    'id': listing.id,
                    'title': property.title,
                    'distance': round(distance, 2),
                    'monthly_rental': float(listing.monthly_rental),
                    'bedrooms': property.bedroom,
                    'bathrooms': property.bathroom
                })

    return jsonify(nearby_listings)

def is_property_available(property_id, start_date):
    calendar_entries = Calendar.query.filter_by(property_id=property_id).all()

    for entry in calendar_entries:
        if entry.status == 'unavailable' and entry.date_start <= start_date <= entry.date_end:
            return False  

    return True

# ========================================== Results

@listing_routes.route('/results', methods=['GET'])
def results():
    city = request.args.get('city')
    start_date_str = request.args.get('start_date')
    page = request.args.get('page', 1, type=int)

    if not city:
        flash('Please enter a city name.', 'danger')
        return redirect(url_for('some_other_route'))

    city_coordinates = get_coordinates(city)
    if not city_coordinates:
        flash('Invalid city name.', 'danger')
        return redirect(url_for('search_routes.search'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
        return redirect(url_for('search_routes.search'))

    properties = Property.query.filter_by(city=city).all()

    listings = []
    for property in properties:
        listing = Listing.query.filter_by(property_id=property.id).first()
        if listing:
            # Calculate distance between city and property
            property_coordinates = (property.latitude, property.longitude)
            distance = geodesic(city_coordinates, property_coordinates).km

            if distance <= 10 and listing.avaiable_start_date <= start_date:
                # Check calendar availability
                if is_property_available(property.id, start_date):
                    thumbnail = Photo.query.filter_by(property_id=property.id, is_thumbnail=True).first()
                    listing.thumbnail = thumbnail
                    listings.append(listing)

    per_page = 20
    start = (page - 1) * per_page
    end = start + per_page
    paginated_listings = listings[start:end]

    has_next = len(listings) > end
    has_prev = page > 1

    return render_template(
        'results.html',
        listings=paginated_listings,
        city=city,
        page=page,
        has_next=has_next,
        has_prev=has_prev
    )

# ======================================================== See Full Property

@listing_routes.route('/listing/<int:listing_id>')
def listing_details(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    property = listing.property  # Access the related Property object

    property_features = {
        "bedrooms": property.bedroom,
        "garage": property.garage,
        "kitchen": property.kitchen,
        "swimming_pool": property.swimming_pool,
        "garden": property.garden,
        "air_conditioning": property.air_conditioning,
        "heating": property.heating,
        "gym": property.gym,
        "laundry": property.laundry,
        "fireplace": property.fireplace,
        "balcony": property.balcony,
        "pet_friendly": property.pet_friendly,
        "bbq_area": property.bbq_area,
        "jacuzzi": property.jacuzzi,
        "tennis_court": property.tennis_court
    }
    suburb = property.suburb
    city = property.city
    state_id = property.state_id
    country_id = property.country_id

    photos = Photo.query.filter_by(property_id=listing.property_id).all()
    all_photos = [photo.file_path for photo in photos]

    thumbnail_photo = Photo.query.filter_by(property_id=listing.property_id, is_thumbnail=True).first()
    if thumbnail_photo:
        thumbnail_photo = thumbnail_photo.file_path

    return render_template(
        'listing_details.html',
        listing=listing,
        property=property,
        all_photos=all_photos,
        thumbnail_photo=thumbnail_photo,
        property_features=property_features,
        suburb=suburb,
        city=city,
        state_id=state_id,
        country_id=country_id,
        show_schedule_button=True 
    )

@listing_routes.route('/listing/<int:listing_id>/get_availability')
def get_availability(listing_id):
    # Get the listing and associated property
    listing = Listing.query.get_or_404(listing_id)
    property = listing.property

    # Get calendar entries for the property
    calendar_entries = Calendar.query.filter_by(property_id=property.id).all()

    # Format availability data for the calendar
    availability = []
    for entry in calendar_entries:
        availability.append({
            'start': entry.date_start.isoformat(),
            'end': entry.date_end.isoformat(),
            'status': entry.status
        })

    return jsonify(availability)

>>>>>>> origin/main
