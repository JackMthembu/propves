from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from models import Wishlist, Listing
from flask_login import current_user, login_required
from extensions import db

wishlist_routes = Blueprint('wishlist_routes', __name__)

@wishlist_routes.route('/wishlist')
@login_required
def wishlist():
    user_wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()
    listings = []
    
    if user_wishlist:
        # Use the relationship defined in the model instead of iterating
        listings = user_wishlist.listings

    return render_template('wishlist.html', listings=listings)

@wishlist_routes.route('/add_to_wishlist/<int:listing_id>', methods=['POST'])
@login_required
def add_to_wishlist(listing_id):
    # Get the listing first to ensure it exists
    listing = Listing.query.get_or_404(listing_id)
    
    user_wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()
    if not user_wishlist:
        user_wishlist = Wishlist(user_id=current_user.id)
        db.session.add(user_wishlist)
        
    # Check if listing is already in wishlist using the relationship
    if listing not in user_wishlist.listings:
        user_wishlist.listings.append(listing)
        db.session.commit()
        flash('Listing added to wishlist!', 'success')
    else:
        flash('Listing is already in your wishlist.', 'info')

    return redirect(url_for('search_routes.results'))

@wishlist_routes.route('/remove_from_wishlist/<int:listing_id>', methods=['POST'])
@login_required
def remove_from_wishlist(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    user_wishlist = Wishlist.query.filter_by(user_id=current_user.id).first()

    if user_wishlist and listing in user_wishlist.listings:
        user_wishlist.listings.remove(listing)
        db.session.commit()
        flash('Listing removed from wishlist!', 'success')

    return redirect(url_for('wishlist_routes.wishlist'))