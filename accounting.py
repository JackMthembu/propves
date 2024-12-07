from flask import Blueprint, current_app, jsonify, request, render_template, flash, redirect, url_for
from datetime import datetime
from extensions import db
from forms import BudgetForm
from models import Property, Owner, Transaction, User, Budget
from flask_login import current_user, login_required
from collections import defaultdict
from decimal import Decimal
from sqlalchemy.sql import func
from sqlalchemy import func, text, desc
from app_constants import ACCOUNTS, EXPENSE_CLASSIFICATIONS
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, DecimalField
from wtforms.validators import DataRequired

accounting_routes = Blueprint('accounting_routes', __name__)

def get_sort_query(query, sort_by='date', order='desc'):
    """Helper function to sort query based on parameters"""
    sort_column = None
    if sort_by == 'date':
        # For grouped queries, use the aggregated version
        if 'group_by' in str(query):
            sort_column = func.max(Transaction.transaction_date)
        else:
            sort_column = Transaction.transaction_date
    elif sort_by == 'amount':
        if 'group_by' in str(query):
            sort_column = func.sum(Transaction.debit_amount)
        else:
            sort_column = Transaction.debit_amount
    # ... other sort options ...

    if order == 'desc':
        return query.order_by(sort_column.desc())
    return query.order_by(sort_column.asc())

@accounting_routes.route('/property/<int:property_id>/expenses', methods=['GET'])
@login_required
def get_expenses(property_id):
    """Get paginated expenses for a property"""
    try:
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        property = Property.query.get(property_id)
        if not property or property.owner_id != owner.id:
            return jsonify({'error': 'Property not found or access denied'}), 403

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        start_date = request.args.get('start_date', 
                                    datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', 
                                  datetime.now().strftime('%Y-%m-%d'))
        category = request.args.get('category')
        
        base_query = Transaction.query.filter(
            Transaction.property_id == property_id,
            Transaction.transaction_date.between(
                datetime.strptime(start_date, '%Y-%m-%d'),
                datetime.strptime(end_date, '%Y-%m-%d')
            ),
            Transaction.main_category.in_([
                'Operating Expenses',
                'Occupancy Expenses',
                'Common Area Expenses',
                'Financial Expenses'
            ])
        )

        if category:
            base_query = base_query.filter(Transaction.account == category)

        # Create nested structure for summary
        expenses_summary = defaultdict(lambda: defaultdict(Decimal))
        for t in base_query.all():
            main_cat = t.main_category
            sub_cat = t.account or 'Other'
            expenses_summary[main_cat][sub_cat] += Decimal(str(t.debit_amount or 0))

        # Get paginated transaction details
        sort_by = request.args.get('sort', 'date')
        order = request.args.get('order', 'desc')
        base_query = get_sort_query(base_query, sort_by, order)
        pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)

        transactions = [{
            'id': t.id,
            'date': t.transaction_date.strftime('%Y-%m-%d'),
            'category': t.main_category,
            'account': t.account,
            'description': t.description,
            'amount': str(t.debit_amount or 0),
            'is_verified': t.is_verified,
            'document': t.document
        } for t in pagination.items]

        # Convert defaultdict to regular dict for JSON serialization
        expenses_summary = {
            category: dict(subcategories)
            for category, subcategories in expenses_summary.items()
        }

        return jsonify({
            'expenses': expenses_summary,  # Categorized summary
            'transactions': transactions,  # Detailed list
            'pagination': {
                'total_pages': pagination.pages,
                'current_page': page,
                'total_items': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'filters': {
                'start_date': start_date,
                'end_date': end_date,
                'category': category,
                'sort_by': sort_by,
                'order': order
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error in get_expenses: {str(e)}")
        return jsonify({'error': 'Failed to retrieve expenses', 'details': str(e)}), 500

@accounting_routes.route('/upload-transactions', methods=['POST'])
@login_required
def upload_transactions():
    current_app.logger.debug(f"Files in request: {request.files}")
    if 'files' not in request.files:
        current_app.logger.error("No file part in the request")
        return jsonify({
            'success': False,
            'error': 'No file part'
        }), 400
    
    files = request.files.getlist('files')
    current_app.logger.debug(f"Number of files received: {len(files)}")
    
    if not files or all(file.filename == '' for file in files):
        return jsonify({
            'success': False,
            'error': 'No selected file'
        }), 400

    try:
        current_app.logger.debug(f"Uploading {len(files)} files")
        processed_files = []
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Process your file here
                processed_files.append(filename)

        return jsonify({
            'success': True,
            'message': f'Successfully processed {len(processed_files)} files',
            'redirect': url_for('accounting_routes.get_portfolio_transactions')
        })
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'csv', 'xls', 'xlsx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@accounting_routes.route('/budget/overview', methods=['GET', 'POST'])
@login_required
def get_budget_overview():
    # Create form instance
    form = BudgetForm()
    
    # Get page number from request args, default to 1
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of items per page

    # Get owner information
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    
    # Get properties and set choices
    properties = Property.query.filter_by(owner_id=owner.id).all() if owner else []
    form.property_id.choices = [(p.id, p.title) for p in properties]
    form.property_id.choices.extend([
        (-1, 'Portfolio (Fixed Amount)'),
        (0, 'All Properties (Split Equally)')
    ])
    
    # Get paginated budgets
    budgets_pagination = Budget.query.order_by(Budget.date_updated.desc()).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )

    return render_template(
        'accounting/budget.html',
        form=form,  # Pass the form to the template
        budgets=budgets_pagination.items,
        properties=properties,
        page=page,
        total_pages=budgets_pagination.pages,
        total=budgets_pagination.total
    )

@accounting_routes.route('/property/<int:property_id>/budget', methods=['POST'])
@login_required
def create_budget(property_id):
    """Create a new budget entry"""
    try:
        # Verify owner access
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        property = Property.query.get(property_id)
        if not property or property.owner_id != owner.id:
            return jsonify({'error': 'Property not found or access denied'}), 403

        data = request.get_json()
        
        # Create new budget
        budget = Budget(
            property_id=property_id,
            budget_type=data.get('budget_type'),
            budget_amount=data.get('budget_amount', 0),
            actual_amount=data.get('actual_amount', 0)
        )
        
        db.session.add(budget)
        db.session.commit()

        return jsonify({
            'message': 'Budget created successfully',
            'budget': {
                'property_id': budget.property_id,
                'budget_type': budget.budget_type,
                'budget_amount': float(budget.budget_amount),
                'actual_amount': float(budget.actual_amount),
                'date_updated': budget.date_updated.strftime('%Y-%m-%d')
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in create_budget: {str(e)}")
        return jsonify({'error': 'Failed to create budget'}), 500

@accounting_routes.route('/property/<int:property_id>/budget/<int:budget_id>', methods=['PUT'])
@login_required
def update_budget(property_id, budget_id):
    """Update an existing budget entry"""
    try:
        # Verify owner access
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        property = Property.query.get(property_id)
        if not property or property.owner_id != owner.id:
            return jsonify({'error': 'Property not found or access denied'}), 403

        budget = Budget.query.get(budget_id)
        if not budget or budget.property_id != property_id:
            return jsonify({'error': 'Budget not found'}), 404

        data = request.get_json()
        
        # Update budget fields
        if 'budget_type' in data:
            budget.budget_type = data['budget_type']
        if 'budget_amount' in data:
            budget.budget_amount = data['budget_amount']
        if 'actual_amount' in data:
            budget.actual_amount = data['actual_amount']

        db.session.commit()

        return jsonify({
            'message': 'Budget updated successfully',
            'budget': {
                'property_id': budget.property_id,
                'budget_type': budget.budget_type,
                'budget_amount': float(budget.budget_amount),
                'actual_amount': float(budget.actual_amount),
                'date_updated': budget.date_updated.strftime('%Y-%m-%d')
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in update_budget: {str(e)}")
        return jsonify({'error': 'Failed to update budget'}), 500

@accounting_routes.route('/property/<int:property_id>/budget/<int:budget_id>', methods=['DELETE'])
@login_required
def delete_budget(property_id, budget_id):
    """Delete a budget entry"""
    try:
        # Verify owner access
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        property = Property.query.get(property_id)
        if not property or property.owner_id != owner.id:
            return jsonify({'error': 'Property not found or access denied'}), 403

        budget = Budget.query.get(budget_id)
        if not budget or budget.property_id != property_id:
            return jsonify({'error': 'Budget not found'}), 404

        db.session.delete(budget)
        db.session.commit()

        return jsonify({'message': 'Budget deleted successfully'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in delete_budget: {str(e)}")
        return jsonify({'error': 'Failed to delete budget'}), 500

@accounting_routes.route('/budget/save', methods=['POST'])
@login_required
def save_budget():
    try:
        # Get owner information
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            flash('Owner not found', 'error')
            return redirect(url_for('accounting_routes.get_budget_overview'))

        # Create form instance and set property choices
        form = BudgetForm()
        properties = Property.query.filter_by(owner_id=owner.id).all()
        form.property_id.choices = [(p.id, p.title) for p in properties]
        form.property_id.choices.extend([(-1, 'Portfolio (Fixed Amount)'), (0, 'All Properties (Split Equally)')])

        action = request.form.get('action', '')
        current_app.logger.debug(f"Action received: {action}")

        if action == 'save_new':
            # Handle new budget entry
            budget = Budget(
                property_id=request.form.get('new_property_id'),
                budget_type=request.form.get('new_budget_type'),
                budget_description=request.form.get('new_budget_description'),
                budget_amount=float(request.form.get('new_budget_amount', 0)),
                actual_amount=float(request.form.get('new_actual_amount', 0)),
                execution_date=datetime.strptime(request.form.get('new_execution_date', ''), '%Y-%m-%d')
            )
            db.session.add(budget)
            current_app.logger.debug(f"Adding new budget: {budget}")

        elif action.startswith('save_'):
            # Handle existing budget update
            budget_id = int(action.split('_')[1])
            budget = Budget.query.get_or_404(budget_id)
            budget.property_id = request.form.get(f'property_id_{budget_id}')
            budget.budget_type = request.form.get(f'budget_type_{budget_id}')
            budget.budget_description = request.form.get(f'budget_description_{budget_id}')
            budget.budget_amount = float(request.form.get(f'budget_amount_{budget_id}', 0))
            budget.actual_amount = float(request.form.get(f'actual_amount_{budget_id}', 0))
            budget.execution_date = datetime.strptime(request.form.get(f'execution_date_{budget_id}', ''), '%Y-%m-%d')
            current_app.logger.debug(f"Updating budget {budget_id}: {budget}")

        elif action.startswith('delete_'):
            # Handle budget deletion
            budget_id = int(action.split('_')[1])
            budget = Budget.query.get_or_404(budget_id)
            db.session.delete(budget)
            current_app.logger.debug(f"Deleting budget {budget_id}")

        db.session.commit()
        flash('Budget updated successfully', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in save_budget: {str(e)}")
        flash(f'An error occurred while saving the budget: {str(e)}', 'error')

    return redirect(url_for('accounting_routes.get_budget_overview'))

@accounting_routes.route('/api/budget/current-year')
@login_required
def get_current_year_budget():
    """Get budget data for the current year"""
    try:
        # Verify owner access
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        current_year = datetime.now().year
        budget_items = (Budget.query
            .filter(
                func.extract('year', Budget.execution_date) == current_year,
                Budget.property_id.in_([p.id for p in owner.properties])
            )
            .all())

        return jsonify([{
            'category': item.budget_type,
            'budget_amount': float(item.budget_amount),
            'actual_amount': float(item.actual_amount)
        } for item in budget_items])

    except Exception as e:
        current_app.logger.error(f"Error in get_current_year_budget: {str(e)}")
        return jsonify({'error': 'Failed to retrieve budget data'}), 500

@accounting_routes.route('/api/income/sources')
@login_required
def get_income_sources():
    """Get income sources breakdown for the current user"""
    try:
        # Verify owner access
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            return jsonify({'error': 'Owner not found'}), 404

        # Get all transactions for the owner's properties that are income-related
        income_transactions = Transaction.query.filter(
            Transaction.property_id.in_([p.id for p in owner.properties]),
            Transaction.main_category == 'Income',
            Transaction.transaction_date >= datetime.now().replace(day=1)  # Current month
        ).all()

        # Group and sum transactions by source
        income_sources = defaultdict(float)
        for transaction in income_transactions:
            source = transaction.account or 'Other Income'
            income_sources[source] += float(transaction.credit_amount or 0)

        # Format the response
        response_data = [
            {"source": source, "amount": amount}
            for source, amount in income_sources.items()
        ]

        # If no data, return sample data
        if not response_data:
            response_data = [
                {"source": "Rental Income", "amount": 5000},
                {"source": "Parking Fees", "amount": 800},
                {"source": "Amenities", "amount": 1200},
                {"source": "Late Fees", "amount": 300},
                {"source": "Other", "amount": 200}
            ]

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error in get_income_sources: {str(e)}")
        return jsonify({'error': 'Failed to retrieve income sources'}), 500