from flask import Blueprint, jsonify, request, current_app
from models import State, Country, Budget, Owner, Transaction
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import extract, func
from extensions import db

api_routes = Blueprint('api_routes', __name__)

@api_routes.route('/get_states/<int:country_id>')
@login_required
def get_states(country_id):
    """Get states for a given country"""
    try:
        states = State.query.filter_by(country_id=country_id).all()
        return jsonify([{
            'id': state.id,
            'name': state.state
        } for state in states])
    except Exception as e:
        current_app.logger.error(f"Error fetching states: {str(e)}")
        return jsonify({'error': 'Error fetching states'}), 500

@api_routes.route('/get_countries')
@login_required
def get_countries():
    """Get all countries"""
    try:
        countries = Country.query.all()
        return jsonify([{
            'id': country.id,
            'name': country.country
        } for country in countries])
    except Exception as e:
        current_app.logger.error(f"Error fetching countries: {str(e)}")
        return jsonify({'error': 'Error fetching countries'}), 500

# Add more API endpoints as needed
@api_routes.route('/validate_address', methods=['POST'])
@login_required
def validate_address():
    """Validate an address using Google Maps API"""
    try:
        data = request.get_json()
        # Add your address validation logic here
        return jsonify({'status': 'valid'})
    except Exception as e:
        current_app.logger.error(f"Error validating address: {str(e)}")
        return jsonify({'error': 'Error validating address'}), 500 
    

@api_routes.route('/api/budget/current-year')
@login_required
def get_current_year_budget():
    """Get budget data for the current year"""
    try:
        # Verify owner access
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        current_year = datetime.utcnow().year
        
        # Query budgets for the current year for owner's properties
        budgets = Budget.query.filter(
            extract('year', Budget.execution_date) == current_year,
            Budget.property_id.in_([p.id for p in owner.properties])
        ).all()
        
        # Format the data for the chart
        budget_data = [{
            'budget_type': budget.budget_type,
            'budget_amount': float(budget.budget_amount),
            'actual_amount': float(budget.actual_amount)
        } for budget in budgets]
        
        return jsonify(budget_data)

    except Exception as e:
        current_app.logger.error(f"Error in get_current_year_budget: {str(e)}")
        return jsonify({'error': 'Failed to retrieve budget data'}), 500

@api_routes.route('/api/monthly-financials')
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

        # Get monthly income (Revenue transactions)
        income_results = db.session.query(
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.owner_id == owner.id,
            Transaction.main_category == 'Revenue',
            extract('year', Transaction.transaction_date) == current_year
        ).group_by(
            extract('month', Transaction.transaction_date)
        ).all()

        # Get monthly expenses (Expenses transactions)
        expense_results = db.session.query(
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.owner_id == owner.id,
            Transaction.main_category == 'Expenses',
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

@api_routes.route('/api/expenses-data')
@login_required
def get_expenses_data():
    # Get current month's start and end dates
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1)
    if today.month == 12:
        end_date = datetime(today.year + 1, 1, 1)
    else:
        end_date = datetime(today.year, today.month + 1, 1)

    # Define the subcategories to filter
    subcategories_to_filter = [
        'Administrative Expenses',
        'Utilities',
        'Common Area Expenses',
        'Financial Expenses',
        'Marketing Expenses',
        'Property Management Expenses'
    ]

    # Query transactions grouped by sub_category for expenses
    expenses = db.session.query(
        Transaction.sub_category,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date,
        Transaction.main_category == 'Expenses',
        Transaction.owner_id == current_user.id,
        Transaction.sub_category.in_(subcategories_to_filter)  # Filter by subcategories
    ).group_by(Transaction.sub_category).all()

    # Log the results for debugging
    current_app.logger.debug(f"Filtered expenses: {expenses}")

    # Create series with the corresponding totals
    series = [{'sub_category': expense.sub_category, 'total': float(expense.total)} for expense in expenses]

    return jsonify(series)  # Return the series directly