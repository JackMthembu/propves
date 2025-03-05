from functools import wraps
from flask import current_app
import requests
from datetime import datetime
import uuid

def get_paystack_headers(secret_key):
    """Generate headers for Paystack API requests"""
    return {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json"
    }

def generate_reference():
    """Generate a unique reference for transactions"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    return f"PAY-{timestamp}-{unique_id}"

def initialize_payment(amount, email, callback_url=None, reference=None):
    """Initialize a payment transaction with Paystack"""
    try:
        url = "https://api.paystack.co/transaction/initialize"
        secret_key = current_app.config['PAYSTACK_SECRET_KEY']
        
        data = {
            "amount": int(amount * 100),  # Convert to kobo/cents
            "email": email,
            "reference": reference or generate_reference(),
            "callback_url": callback_url
        }
        
        response = requests.post(
            url,
            headers=get_paystack_headers(secret_key),
            json=data
        )
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Paystack initialization error: {str(e)}")
        return None

def verify_payment(reference):
    """Verify a payment transaction with Paystack"""
    try:
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        secret_key = current_app.config['PAYSTACK_SECRET_KEY']
        
        response = requests.get(
            url,
            headers=get_paystack_headers(secret_key)
        )
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Paystack verification error: {str(e)}")
        return None

def get_payment_status(verification_response):
    """Extract payment status from verification response"""
    if not verification_response or 'data' not in verification_response:
        return False, "Invalid verification response"
    
    data = verification_response['data']
    status = data.get('status', '').lower()
    
    if status == 'success':
        return True, "Payment successful"
    elif status == 'failed':
        return False, "Payment failed"
    else:
        return False, f"Unknown payment status: {status}" 