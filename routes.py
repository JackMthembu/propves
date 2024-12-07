from ast import main
import os
<<<<<<< HEAD
from flask import Blueprint, abort, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from models import Property, Listing, RentalAgreement
=======
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from extensions import db
from forms import ProfileForm, ProfilePicForm
from models import Country, Property
>>>>>>> origin/main

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def dashboard():
<<<<<<< HEAD
    listing = Listing.query.first()

    if listing is None:
        return render_template('dashboard.html', listing=None, rental_agreements=[])

    rental_agreements = RentalAgreement.query.filter_by(listing_id=listing.id).all()

    return render_template('dashboard.html', listing=listing, rental_agreements=rental_agreements)
=======
    return render_template('dashboard.html')
>>>>>>> origin/main

@main.route('/pricing-rtl')
def pricing_rtl():
    return render_template('pricing-rtl.html')

@main.route('/pricing')
def pricing():
    return render_template('pricing.html')

@main.route('/maintenance')
def maintenance():
    return render_template('maintenance.html')

@main.route('/properties')
@login_required
def properties():
    if property.owner_id != current_user.owner_id and current_user.manager_id is None:
        abort(403)         
        flash('You do not have any properties associated with your account.', 'danger')
        return redirect(url_for('route.dashboard'))  

    properties = Property.query.filter_by(owner_id=current_user.owner_id).all()
    return render_template('properties.html', properties=properties)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

# Ensure the directory exists using current_app
def ensure_upload_folder_exists():
    if not os.path.exists(current_app.config['UPLOAD_FOLDER_PROFILE']):
        os.makedirs(current_app.config['UPLOAD_FOLDER_PROFILE'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['png', 'jpg', 'jpeg']

