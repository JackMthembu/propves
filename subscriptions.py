from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from models import db, Subscription, Owner
from forms import SubscriptionUpdatesForm
from utils.payment import initialize_payment, verify_payment, get_payment_status
from datetime import datetime

subscription_routes = Blueprint('subscription_routes', __name__)

@subscription_routes.route('/subscriptions')
@login_required
def subscriptions():
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    if not owner:
        flash('Owner profile not found.', 'danger')
        return redirect(url_for('main.dashboard'))
        
    current_subscription = Subscription.query.filter_by(owner_id=owner.id).first()
    
    return render_template('subscriptions/index.html',
                         subscription=current_subscription)

@subscription_routes.route('/subscribe/<plan>', methods=['POST'])
@login_required
def subscribe(plan):
    try:
        # Get plan details and amount
        amount = get_plan_amount(plan)
        
        # Initialize payment
        callback_url = url_for('subscription_routes.verify_payment_callback', _external=True)
        payment_response = initialize_payment(
            amount=amount,
            email=current_user.email,
            callback_url=callback_url
        )
        
        if payment_response and payment_response.get('status'):
            # Store payment reference in session
            session['payment_reference'] = payment_response['data']['reference']
            session['subscription_plan'] = plan  # Also store the plan
            
            # Redirect to payment page
            return redirect(payment_response['data']['authorization_url'])
        else:
            flash('Error initializing payment.', 'danger')
            
    except Exception as e:
        current_app.logger.error(f"Subscription error: {str(e)}")
        flash('An error occurred while processing your subscription.', 'danger')
    
    return redirect(url_for('subscription_routes.subscriptions'))

@subscription_routes.route('/verify-payment')
@login_required
def verify_payment_callback():
    try:
        # Get reference from session or query parameters
        reference = request.args.get('reference') or session.get('payment_reference')
        if not reference:
            flash('No payment reference found.', 'danger')
            return redirect(url_for('subscription_routes.subscriptions'))
        
        # Verify the payment
        verification_response = verify_payment(reference)
        success, message = get_payment_status(verification_response)
        
        if success:
            # Get plan from session
            plan = session.get('subscription_plan')
            # Update subscription with plan details
            update_subscription(current_user.id, verification_response, plan)
            
            # Clear session data
            session.pop('payment_reference', None)
            session.pop('subscription_plan', None)
            
            flash('Subscription updated successfully!', 'success')
        else:
            flash(f'Payment verification failed: {message}', 'danger')
            
    except Exception as e:
        current_app.logger.error(f"Payment verification error: {str(e)}")
        flash('An error occurred while verifying your payment.', 'danger')
    
    return redirect(url_for('subscription_routes.subscriptions'))

def get_plan_amount(plan):
    """Get amount for subscription plan"""
    plans = {
        'basic': 1000,
        'premium': 2000,
        'enterprise': 5000
    }
    return plans.get(plan, 1000)

def update_subscription(user_id, payment_data, plan=None):
    """Update user subscription after successful payment"""
    try:
        owner = Owner.query.filter_by(user_id=user_id).first()
        if not owner:
            raise ValueError("Owner not found")
            
        subscription = Subscription.query.filter_by(owner_id=owner.id).first()
        if not subscription:
            subscription = Subscription(owner_id=owner.id)
            
        # Update subscription details
        subscription.status = 'active'
        subscription.plan = plan if plan else 'basic'  # Default to basic if no plan specified
        subscription.last_payment_date = datetime.utcnow()
        subscription.payment_reference = payment_data['data']['reference']
        
        db.session.add(subscription)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating subscription: {str(e)}")
        raise
