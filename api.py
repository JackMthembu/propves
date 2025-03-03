from flask import Blueprint, jsonify, request, current_app, g, render_template
from models import State, Country, Budget, Owner, Transaction, Banks, Property
from flask_login import login_required, current_user
from datetime import datetime, timedelta
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
    

# @api_routes.route('/api/budget/current-year')
# @login_required
# def get_current_year_budget():
#     """Get budget data for the current year"""
#     try:
#         current_year = datetime.utcnow().year
        
#         # Query budgets for the current year for properties owned by the current user
#         budgets = Budget.query.filter(
#             extract('year', Budget.execution_date) == current_year,
#             Budget.property.has(Owner.user_id == current_user.id)  # Limit to properties owned by the current user's ID
#         ).all()
        
#         # Format the data for the chart
#         budget_data = [{
#             'budget_type': budget.budget_type,
#             'budget_amount': float(budget.budget_amount),
#             'actual_amount': float(budget.actual_amount)
#         } for budget in budgets]
        
#         return jsonify(budget_data)

#     except Exception as e:
#         current_app.logger.error(f"Error in get_current_year_budget: {str(e)}")
#         return jsonify({'error': 'Failed to retrieve budget data'}), 500

@api_routes.route('/api/monthly-financials')
@login_required
def monthly_financials():
    try:
        # Get the date range for the past 365 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        # Get owner's transactions
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Base query for owner's transactions in the past 365 days
        base_query = Transaction.query.filter(
            Transaction.owner_id == owner.id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.is_reconciled == True  # Only include reconciled transactions
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
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.is_reconciled == True  # Only include reconciled transactions
        ).group_by(
            extract('month', Transaction.transaction_date)
        ).all()

        # Get monthly expenses (Expenses transactions)
        expense_results = db.session.query(
            extract('month', Transaction.transaction_date).label('month'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.owner_id == owner.id,
            Transaction.sub_category == 'Cost of Sales',
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.is_reconciled == True  # Only include reconciled transactions
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

@login_required
def get_banks(country_id):
    """Get banks for a given country"""
    try:
        banks = Banks.query.filter_by(country_id=country_id).all()
        return jsonify([{
            'id': bank.id,
            'bank_name': bank.bank_name
        } for bank in banks])
    except Exception as e:
        current_app.logger.error(f"Error fetching banks: {str(e)}")
        return jsonify({'error': 'Error fetching banks'}), 500

@api_routes.route('/api/expenses-summary')
@login_required
def expenses_summary():
    try:
        # Get the date range based on the filter type
        start_date, end_date = transaction_data_filter()  # Call the filter function

        # Get the owner associated with the current user
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Query to sum expenses for the specified date range
        expenses_data = db.session.query(
            Transaction.sub_category,
            func.sum(Transaction.amount).label('total_amount')
        ).filter(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.main_category == 'Expenses',
            Transaction.is_reconciled == True,  # Only include reconciled transactions
            Transaction.property_id.in_([p.id for p in owner.properties])  # Limit to properties owned by the current user
        ).group_by(Transaction.sub_category).all()

        # Convert the results to a dictionary for easier access
        summary_dict = {sub_category: float(total_amount) for sub_category, total_amount in expenses_data}

        return jsonify(summary_dict)  # Return the summary as JSON
    except Exception as e:
        current_app.logger.error(f"Error fetching expenses summary: {str(e)}")
        return jsonify({'error': 'Failed to fetch expenses summary'}), 500

def get_expenses_summary(filter_type):
    # Determine the date range based on the filter type
    if filter_type == 'this_month':
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(day=1, month=datetime.now().month + 1, hour=0, minute=0, second=0, microsecond=0) if datetime.now().month < 12 else datetime.now().replace(year=datetime.now().year + 1, month=1, day=1)
    elif filter_type == 'this_year':
        start_date = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(month=1, day=1, year=datetime.now().year + 1)
    elif filter_type == 'past_year':
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
    else:
        # Default to the last 12 months if the filter type is not recognized
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

    # Query to sum amounts grouped by sub_category where main_category is 'Expenses'
    expense_summary = db.session.query(
        Transaction.sub_category,
        func.sum(Transaction.amount).label('total_amount')
    ).filter(
        Transaction.main_category == 'Expenses',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date,
        Transaction.is_reconciled == True  # Only include reconciled transactions
    ).group_by(
        Transaction.sub_category
    ).all()

    # Convert the results to a dictionary for easier access
    summary_dict = {sub_category: float(total_amount) for sub_category, total_amount in expense_summary}

    return summary_dict

@api_routes.route('/api/income-summary')
@login_required
def income_summary():
    try:
        # Get the date range based on the filter type
        start_date, end_date = transaction_data_filter()  # Call the filter function

        # Get the owner associated with the current user
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Query to sum income for the specified date range
        income_data = db.session.query(
            Transaction.sub_category,
            func.sum(Transaction.amount).label('total_amount')
        ).filter(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.main_category == 'Revenue',
            Transaction.is_reconciled == True,  # Only include reconciled transactions
            Transaction.property_id.in_([p.id for p in owner.properties])  # Limit to properties owned by the current user
        ).group_by(Transaction.sub_category).all()

        # Convert the results to a dictionary for easier access
        summary_dict = {sub_category: float(total_amount) for sub_category, total_amount in income_data}

        return jsonify(summary_dict)  # Return the summary as JSON
    except Exception as e:
        current_app.logger.error(f"Error fetching income summary: {str(e)}")
        return jsonify({'error': 'Failed to fetch income summary'}), 500

def get_income_summary(filter_type):
    # Determine the date range based on the filter type
    if filter_type == 'this_month':
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(day=1, month=datetime.now().month + 1, hour=0, minute=0, second=0, microsecond=0) if datetime.now().month < 12 else datetime.now().replace(year=datetime.now().year + 1, month=1, day=1)
    elif filter_type == 'this_year':
        start_date = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(month=1, day=1, year=datetime.now().year + 1)
    elif filter_type == 'past_year':
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
    else:
        # Default to the last 12 months if the filter type is not recognized
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

    # Query to sum amounts grouped by sub_category where main_category is 'Expenses'
    income_summary = db.session.query(
        Transaction.sub_category,
        func.sum(Transaction.amount).label('total_amount')
    ).filter(
        Transaction.main_category == 'Revenue',
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date,
        Transaction.is_reconciled == True  # Only include reconciled transactions
    ).group_by(
        Transaction.sub_category
    ).all()

    # Convert the results to a dictionary for easier access
    summary_dict = {sub_category: float(total_amount) for sub_category, total_amount in income_summary}

    return summary_dict

@api_routes.route('/api/budget-summary', methods=['GET'])
@login_required
def budget_summary():
    try:
        # Get the date range based on the filter type
        start_date, end_date = transaction_data_filter()  # Call the filter function

        # Get the owner associated with the current user
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Query to sum budget amounts grouped by budget type for the specified date range
        budget_data = db.session.query(
            Budget.budget_type,
            db.func.sum(Budget.budget_amount).label('total_budget')
        ).filter(
            Budget.execution_date >= start_date,
            Budget.execution_date <= end_date,  # Use the end date from the filter
            Budget.property_id.in_([p.id for p in owner.properties])  # Limit to properties owned by the current user
        ).group_by(
            Budget.budget_type
        ).all()

        # Convert the results to a dictionary for easier access
        summary_dict = {budget_type: float(total_budget) for budget_type, total_budget in budget_data}

        return jsonify(summary_dict)  # Return the summary as JSON
    except Exception as e:
        current_app.logger.error(f"Error fetching budget summary: {str(e)}")
        return jsonify({'error': 'Failed to fetch budget summary'}), 500

@api_routes.route('/api/property-owner-currency')
@login_required
def property_owner_currency():
    # Assuming you have a way to get the current user's property owner
    owner = get_property_owner()  # Replace with your logic to get the owner
    return jsonify({'symbol': owner.currency.symbol})  # Adjust based on your model


@api_routes.route('/api/property/<int:property_id>/owner', methods=['GET'])
@login_required
def get_property_owner(property_id):
    try:
        # Get the property by ID
        property = Property.query.get_or_404(property_id)

        # Access the owner of the property
        owner = property.owner

        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Access the user associated with the owner
        user = owner.user

        if not user:
            return jsonify({'error': 'User not found for this owner'}), 404

        # Return the user details
        return jsonify({
            'owner_id': owner.id,
            'user_id': user.id,
            'username': user.username,  # Adjust based on your User model
            'currency_symbol': user.get_currency_symbol()  # Assuming this method exists
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching property owner: {str(e)}")
        return jsonify({'error': 'Failed to retrieve property owner'}), 500

@api_routes.route('/api/occupancy-level')
@login_required
def occupancy_level():
    try:
        # Get the date range based on the filter type
        start_date, end_date = transaction_data_filter()  # Call the filter function

        # Get the owner associated with the current user
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        occupied_count = db.session.query(func.count(Property.id)).filter(
            Property.status == 'occupied',
            Property.id.in_(
                db.session.query(Transaction.property_id).filter(
                    Transaction.owner_id == owner.id,  # Limit to properties owned by the current user
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date  # Apply date filter
                )
            )
        ).scalar()

        listed_count = db.session.query(func.count(Property.id)).filter(
            Property.status == 'listed',
            Property.id.in_(
                db.session.query(Transaction.property_id).filter(
                    Transaction.owner_id == owner.id,  # Limit to properties owned by the current user
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date  # Apply date filter
                )
            )
        ).scalar()

        # Calculate occupancy level
        occupancy_ratio = occupied_count / listed_count if listed_count > 0 else 0

        return jsonify({
            'occupied': occupied_count,
            'listed': listed_count,
            'occupancy_ratio': occupancy_ratio
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching occupancy level: {str(e)}")
        return jsonify({'error': 'Failed to fetch occupancy level'}), 500

@api_routes.route('/api/operating_expenses_ratio', methods=['GET'])
@login_required
def operating_expenses_ratio():
    """
    Calculates the expense ratio for the specified date range.
    """
    try:
        # Get the date range based on the filter type
        start_date, end_date = transaction_data_filter()  # Call the filter function

        # Get the owner associated with the current user
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Calculate total operating expenses
        operating_expenses = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.sub_category == 'Operating Expenses',
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,  # Apply date filter
            Transaction.owner_id == owner.id
        ).scalar() or 0  # Default to 0 if no expenses

        # Calculate total revenue
        revenue = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.main_category == 'Revenue',
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,  # Apply date filter
            Transaction.owner_id == owner.id
        ).scalar() or 0  # Default to 0 if no revenue

        # Avoid division by zero
        if revenue == 0:
            operating_expenses_ratio = 0
        else:
            operating_expenses_ratio = round((operating_expenses / revenue) * 100, 2)  # Calculate ratio and round to 2 decimal places

        return jsonify({
            'operating_expenses_ratio': operating_expenses_ratio
        })

    except Exception as e:
        current_app.logger.error(f"Error calculating expense ratio: {str(e)}")  # Log the error
        return jsonify({'error': str(e)}), 500


def transaction_data_filter():
    filter_type = request.args.get('filter', 'current_period')  # Default to 'current_period'
    
    # Initialize start and end dates
    start_date = None
    end_date = datetime.now()  # Default end date is now

    # Calculate date ranges based on filter type
    if filter_type == 'this_month':  # Current month
        start_date = datetime.now().replace(day=1)
    elif filter_type == 'past_month':  # Previous month
        start_date = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
        end_date = datetime.now().replace(day=1)
    elif filter_type == 'past_year':  # Past year
        start_date = datetime.now() - timedelta(days=365)
    elif filter_type == 'current_year':  # Current year
        start_date = datetime.now().replace(month=1, day=1)
    elif filter_type == 'today':  # Today
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    else:  # Default to past 365 days
        start_date = datetime.now() - timedelta(days=365)

    return start_date, end_date  # Return the calculated start and end dates
        

@api_routes.route('/api/dashboard-data', methods=['GET'])
@login_required
def dashboard_data():
    try:
        # Get the filter type from the query parameters
        filter_type = request.args.get('filter', 'current_period')  # Default to 'current_period'
        
        # Get the date range based on the filter type
        start_date, end_date = transaction_data_filter()  # Call the filter function

        # Get the owner associated with the current user
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Calculate total income
        total_income = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.main_category == 'Revenue',
            Transaction.owner_id == owner.id
        ).scalar() or 0  # Default to 0 if no income

        # Calculate total expenses
        total_expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.main_category == 'Expenses',
            Transaction.owner_id == owner.id
        ).scalar() or 0  # Default to 0 if no expenses

        # Calculate budget summary
        budget_data = db.session.query(
            Budget.budget_type,
            db.func.sum(Budget.budget_amount).label('total_budget')
        ).filter(
            Budget.execution_date >= start_date,
            Budget.execution_date <= end_date,
            Budget.property_id.in_([p.id for p in owner.properties])  # Limit to properties owned by the current user
        ).group_by(Budget.budget_type).all()

        budget_summary = {budget_type: float(total_budget) for budget_type, total_budget in budget_data}

        # Calculate occupancy level
        occupied_count = db.session.query(func.count(Property.id)).filter(
            Property.status == 'occupied',
            Property.id.in_(
                db.session.query(Transaction.property_id).filter(
                    Transaction.owner_id == owner.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date
                )
            )
        ).scalar() or 0

        listed_count = db.session.query(func.count(Property.id)).filter(
            Property.status == 'listed',
            Property.id.in_(
                db.session.query(Transaction.property_id).filter(
                    Transaction.owner_id == owner.id,
                    Transaction.transaction_date >= start_date,
                    Transaction.transaction_date <= end_date
                )
            )
        ).scalar() or 0

        occupancy_ratio = occupied_count / listed_count if listed_count > 0 else 0

        return jsonify({
            'total_income': float(total_income),
            'total_expenses': float(total_expenses),
            'budget_summary': budget_summary,
            'occupied': occupied_count,
            'listed': listed_count,
            'occupancy_ratio': occupancy_ratio
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard data: {str(e)}")
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500
        
