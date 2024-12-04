from flask import Blueprint, jsonify, request, current_app
from models import State, Country, Budget, Owner
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import extract
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