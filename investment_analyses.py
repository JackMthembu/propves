from celery_config import current_app
from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from sqlalchemy import func
from extensions import db  
from models import Transaction  

investment_analyses_routes = Blueprint('investment_analyses', __name__)

@investment_analyses_routes.route('/oer-analysis', methods=['GET'])
@login_required
def oer_analysis():
    try:
        # Fetch total operating expenses and total income from the database
        total_expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.main_category == 'Expenses',
            Transaction.is_reconciled == True  # Only include reconciled transactions
        ).scalar() or 0  # Default to 0 if no expenses

        total_income = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.main_category == 'Revenue',
            Transaction.is_reconciled == True  # Only include reconciled transactions
        ).scalar() or 1  # Default to 1 to avoid division by zero

        # Calculate OER
        expense_ratio = (total_expenses / total_income) * 100 if total_income > 0 else 0

        # Determine the OER category
        if expense_ratio <= 20:
            oer_category = 'Excellent'
        elif expense_ratio <= 45:
            oer_category = 'Good'
        elif expense_ratio <= 60:
            oer_category = 'Moderate'
        else:
            oer_category = 'Not Good'

        # Log the OER category
        if current_app:
            current_app.logger.info(f"OER Category: {oer_category}")
        else:
            print(f"OER Category: {oer_category}") 

        return render_template('dashboard.html', investment_analyses_oer=oer_category)

    except Exception as e:
        # Use the correct logger from the Flask app
        if current_app:
            current_app.logger.error(f"Error calculating OER: {str(e)}")
        else:
            print(f"Error calculating OER: {str(e)}")  # Fallback if current_app is not available
        return jsonify({'error': 'Failed to calculate OER'}), 500