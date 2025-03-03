from flask import Blueprint, app, current_app, jsonify, request, render_template, flash, redirect, session, url_for, send_file, make_response
from datetime import datetime, timedelta

import requests
from app_constants import ACCOUNT_CLASSIFICATIONS
from extensions import db
from forms import BudgetForm
from models import Property, Owner, Transaction, Budget, User
from flask_login import current_user, login_required
from collections import defaultdict
from decimal import Decimal
from sqlalchemy.sql import func
from sqlalchemy import func
from werkzeug.utils import secure_filename
import csv
import io
import pdfkit
from sqlalchemy.orm import joinedload
from utils import allowed_file
from transaction import transactions

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
    
    # Get paginated budgets for the current user's properties
    budgets_pagination = Budget.query.join(Property).filter(
        Property.owner.has(user_id=current_user.id)
    ).order_by(Budget.date_updated.desc()).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )

    # Get the currency symbol based on the user's currency_id
    currency_symbol = current_user.get_currency_symbol()  # Assuming this method exists in the User model

    return render_template(
        'accounting/budget.html',
        form=form,  # Pass the form to the template
        budgets=budgets_pagination.items,
        properties=properties,
        page=page,
        total_pages=budgets_pagination.pages,
        total=budgets_pagination.total,
        currency_symbol=currency_symbol  # Pass the currency symbol to the template
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

@accounting_routes.route('/income_statement', methods=['GET'])
@login_required
def income_statement():
    # Get date filters from request args
    start_date = request.args.get('start_date', datetime.utcnow().strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))

    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include the end date

    # Data Retrieval: Include only reconciled transactions within the date range
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all() 

    # owner = Owner.query.options(joinedload(Owner.user)).filter_by(user_id=current_user.id).first()

    # Calculations
    revenue = sum(transaction.amount for transaction in transactions if transaction.main_category == 'Revenue')
    cost_of_sales = sum(transaction.amount for transaction in transactions if transaction.sub_category == 'Cost of Sales')
    gross_income = revenue - cost_of_sales

    overhead_expenses = sum(transaction.amount for transaction in transactions if transaction.main_category == 'Expenses' and transaction.sub_category != 'Cost of Sales')
    net_income = gross_income - overhead_expenses

    # Revenue Categorization
    revenue_categories = {
        'Rental Income': 0,
        'Other Income': 0
    }
    
    for transaction in transactions:
        if transaction.main_category == 'Revenue':
            if transaction.sub_category in revenue_categories:
                revenue_categories[transaction.sub_category] += transaction.amount

    # Expense Categorization
    expense_categories = {}
    overhead_expense_categories = {}  
    for transaction in transactions:
        if transaction.main_category == 'Expenses' and transaction.sub_category != 'Cost of Sales':
            category = transaction.sub_category
            expense_categories.setdefault(category, 0)
            expense_categories[category] += transaction.amount

            # Exclude 'Cost of Sales' from overhead expenses
            if category != 'Cost of Sales':  
                overhead_expense_categories.setdefault(category, 0)
                overhead_expense_categories[category] += transaction.amount

    # Calculate total overhead expenses (excluding 'Cost of Sales')
    overhead_expenses = sum(overhead_expense_categories.values())

    # Prepare the response with formatted amounts
    income_statement_data = {
        'income': format_currency(revenue, current_user.currency.symbol),  
        'revenue_categories': {k: format_currency(v, current_user.currency.symbol) for k, v in revenue_categories.items()},
        'cost_of_sales': format_currency(cost_of_sales, current_user.currency.symbol),  
        'gross_income': format_currency(gross_income, current_user.currency.symbol),  
        'overhead_expenses': format_currency(overhead_expenses, current_user.currency.symbol),  
        'net_income': format_currency(net_income, current_user.currency.symbol),  
        'expense_categories': {k: format_currency(v, current_user.currency.symbol) for k, v in expense_categories.items()}, 
        'currency_symbol': current_user.currency.symbol,  
        'overhead_expense_categories': overhead_expense_categories 
    }

    # Pass the datetime module to the template
    return render_template('accounting/income_statement.html', income_statement=income_statement_data, datetime=datetime)

@accounting_routes.route('/balance_sheet', methods=['GET'])
@login_required
def balance_sheet():
    """
    Renders the balance sheet template with calculated financial data.
    """
    # Get date filters from request args, defaulting to today
    start_date_str = request.args.get('start_date', datetime.utcnow().strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))

    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)  # Include the end date

    # Data Retrieval: Include only reconciled transactions within the date range
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all()

    # --- Calculations ---
    # Assets
    assets = 0
    for category, accounts in ACCOUNT_CLASSIFICATIONS['Assets'].items():
        for account in accounts:
            assets += sum(t.amount for t in transactions if t.account == account)

    current_assets = 0
    for account in ACCOUNT_CLASSIFICATIONS['Assets']['Current Assets']:
        current_assets += sum(t.amount for t in transactions if t.account == account)

    non_current_assets = 0
    for account in ACCOUNT_CLASSIFICATIONS['Assets']['Non-Current Assets']:
        non_current_assets += sum(t.amount for t in transactions if t.account == account)

    cash_cash_equivalents = sum(t.amount for t in transactions if t.account == 'Bank')

    accounts_receivable = 0
    for account in ACCOUNT_CLASSIFICATIONS['Assets']['Current Assets']:
        if account in ('Accounts Receivable', 'Prepaid Expenses', 'Prepaid Insurance', 'Prepaid Rent'):
            accounts_receivable += sum(t.amount for t in transactions if t.account == account)

    property_plant_equipment = 0
    for account in ACCOUNT_CLASSIFICATIONS['Assets']['Non-Current Assets']:
        if account in ('Building', 'Equipment', 'Furniture and Fixtures', 'Land', 'Leasehold Improvements'):
            property_plant_equipment += sum(t.amount for t in transactions if t.account == account)

    # Liabilities
    liabilities = 0
    for category, accounts in ACCOUNT_CLASSIFICATIONS['Liabilities'].items():
        for account in accounts:
            liabilities += sum(t.amount for t in transactions if t.account == account)

    current_liabilities = 0
    for account in ACCOUNT_CLASSIFICATIONS['Liabilities']['Current Liabilities']:
        current_liabilities += sum(t.amount for t in transactions if t.account == account)

    non_current_liabilities = 0
    for account in ACCOUNT_CLASSIFICATIONS['Liabilities']['Non-Current Liabilities']:
        non_current_liabilities += sum(t.amount for t in transactions if t.account == account)

    accounts_payable = sum(t.amount for t in transactions if t.account == 'Accounts Payable')
    mortgage_payable = sum(t.amount for t in transactions if t.account == 'Mortgage Payable')

    # Equity
    equity = 0
    for account in ACCOUNT_CLASSIFICATIONS['Equity']:
        equity += sum(t.amount for t in transactions if t.account == account)

    share_capital = 0
    for account in ACCOUNT_CLASSIFICATIONS['Equity']:
        if account in ('Contributed Capital', 'Owner/s Capital', 'Partner Contributions'):
            share_capital += sum(t.amount for t in transactions if t.account == account)

    # ... (rest of your calculations) ...
    dividends = sum(transaction.amount for transaction in transactions if transaction.account == 'Distributions')

    # You'll need a function to calculate retained earnings (replace this)
    retained_earnings = calculate_retained_earnings(transactions)  

    liabilities_equity = liabilities + equity

    # --- Prepare the context for the template ---
    balance_sheet_data = {
        'assets': format_currency(assets, current_user.currency.symbol),
        'current_assets': format_currency(current_assets, current_user.currency.symbol),
        'non_current_assets': format_currency(non_current_assets, current_user.currency.symbol),
        'cash_cash_equivalents': format_currency(cash_cash_equivalents, current_user.currency.symbol),
        'accounts_receivable': format_currency(accounts_receivable, current_user.currency.symbol),
        'property_plant_equipment': format_currency(property_plant_equipment, current_user.currency.symbol),

        'liabilities': format_currency(liabilities, current_user.currency.symbol),
        'current_liabilities': format_currency(current_liabilities, current_user.currency.symbol),
        'non_current_liabilities': format_currency(non_current_liabilities, current_user.currency.symbol),
        'accounts_payable': format_currency(accounts_payable, current_user.currency.symbol),
        'mortgage_payable': format_currency(mortgage_payable, current_user.currency.symbol),

        'equity': format_currency(equity, current_user.currency.symbol),
        'share_capital': format_currency(share_capital, current_user.currency.symbol),
        'dividends': format_currency(dividends, current_user.currency.symbol),
        'retained_earnings': format_currency(retained_earnings, current_user.currency.symbol), 
        'liabilities_equity': format_currency(liabilities_equity, current_user.currency.symbol), 
        'currency_symbol': current_user.currency.symbol,
    }

    return render_template('accounting/balance_sheet.html', balance_sheet=balance_sheet_data, datetime=datetime)

@accounting_routes.route('/income_statement/pdf', methods=['GET'])
@login_required
def download_income_statement_pdf():
    
    # Get date filters from request args
    start_date = request.args.get('start_date', datetime.utcnow().strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))

    # Generate the income statement data
    income_statement_data = generate_income_statement_data()  # Assume this function generates the data

    # Get the currency symbol from the Owner object
    # owner = Owner.query.filter_by(user_id=current_user.id).first()
    # currency_symbol = owner.currency.symbol if owner and owner.currency else '$'  # Default to $ if not found
    
    currency_symbol = current_user.currency.symbol if current_user and current_user.currency else '$'  # Default to $ if not found


    # Render the PDF template to a string
    rendered = render_template('accounting/income_statement_pdf.html', 
                               income_statement=income_statement_data, 
                               start_date=start_date, 
                               end_date=end_date,
                               generated_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                               currency_symbol=currency_symbol)  # Pass the currency symbol

    # Create PDF from HTML
    pdf = pdfkit.from_string(rendered, 'income_statement.pdf')

    # Send the PDF as a response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=income_statement.pdf'
    return response

@accounting_routes.route('/income_statement/csv', methods=['GET'])
@login_required
def download_income_statement_csv():
    # Generate the income statement data
    income_statement_data = generate_income_statement_data()

    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header
    writer.writerow(['Category', 'Amount'])

    # Write revenue categories
    writer.writerow(['Revenue', ''])  # Add a section header for revenue
    for category, amount in income_statement_data['revenue_categories'].items():
        writer.writerow([category, amount])
    writer.writerow(['Total Revenue', income_statement_data['income']])

    # Write cost of sales
    writer.writerow(['Cost of Sales', ''])  # Add a section header for cost of sales
    writer.writerow(['Total Cost of Sales', income_statement_data['cost_of_sales']])

    # Write gross income
    writer.writerow(['Gross Income', income_statement_data['gross_income']])

    # Write overhead expenses
    writer.writerow(['Overhead Expenses', ''])  # Add a section header for overhead expenses
    for category, amount in income_statement_data['expense_categories'].items():
        writer.writerow([category, amount])
    writer.writerow(['Total Overhead Expenses', income_statement_data['overhead_expenses']])

    # Write net income
    writer.writerow(['Net Income', income_statement_data['net_income']])

    # Prepare the response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=income_statement.csv'
    return response

@accounting_routes.route('/balance_sheet/pdf', methods=['GET'])
@login_required
def download_balance_sheet_pdf():
    """
    Generates and downloads a PDF version of the balance sheet.
    """
    # Get date filters from request args
    start_date_str = request.args.get('start_date', datetime.utcnow().strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))

    # Convert string dates to datetime objects (if needed)
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Generate balance sheet data (using the function from your previous code)
    balance_sheet_data = generate_balance_sheet_data(start_date, end_date) 

    currency_symbol = current_user.currency.symbol if current_user and current_user.currency else '$'

    # Render the PDF template
    rendered = render_template('accounting/balance_sheet_pdf.html', 
                               balance_sheet=balance_sheet_data, 
                               start_date=start_date_str,  # Pass the original string 
                               end_date=end_date_str,    # Pass the original string
                               generated_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                               currency_symbol=currency_symbol)

    # Create PDF from HTML
    pdf = pdfkit.from_string(rendered, 'balance_sheet.pdf')

    # Create a response with the PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=balance_sheet.pdf'
    return response


@accounting_routes.route('/balance_sheet/csv', methods=['GET'])
@login_required
def download_balance_sheet_csv():
    """
    Generates and downloads a CSV version of the balance sheet.
    """
    # Get date filters (similar to PDF route)
    start_date_str = request.args.get('start_date', datetime.utcnow().strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Generate balance sheet data
    balance_sheet_data = generate_balance_sheet_data(start_date, end_date)

    # Create CSV output
    output = io.StringIO()
    writer = csv.writer(output)

        # Generate balance sheet data
    balance_sheet_data = generate_balance_sheet_data(start_date, end_date)

    # Create CSV output
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Category', 'Amount'])

    # --- Write Assets ---
    writer.writerow(['Assets', ''])
    writer.writerow(['Current Assets', ''])
    for account in ACCOUNT_CLASSIFICATIONS['Assets']['Current Assets']:
        amount = sum(t.amount for t in transactions if t.account == account)
        writer.writerow([account, format_currency(amount, current_user.currency.symbol)])

    writer.writerow(['Non-Current Assets', ''])
    for account in ACCOUNT_CLASSIFICATIONS['Assets']['Non-Current Assets']:
        amount = sum(t.amount for t in transactions if t.account == account)
        writer.writerow([account, format_currency(amount, current_user.currency.symbol)])
    writer.writerow(['Total Non-Current Assets', balance_sheet_data['non_current_assets']])
    writer.writerow(['Total Assets', balance_sheet_data['assets']])

    # --- Write Liabilities ---
    writer.writerow(['Liabilities', ''])
    writer.writerow(['Current Liabilities', ''])
    for account in ACCOUNT_CLASSIFICATIONS['Liabilities']['Current Liabilities']:
        amount = sum(t.amount for t in transactions if t.account == account)
        writer.writerow([account, format_currency(amount, current_user.currency.symbol)])
    writer.writerow(['Total Current Liabilities', balance_sheet_data['current_liabilities']])

    writer.writerow(['Non-Current Liabilities', ''])
    for account in ACCOUNT_CLASSIFICATIONS['Liabilities']['Non-Current Liabilities']:
        amount = sum(t.amount for t in transactions if t.account == account)
        writer.writerow([account, format_currency(amount, current_user.currency.symbol)])
    writer.writerow(['Total Non-Current Liabilities', balance_sheet_data['non_current_liabilities']])
    writer.writerow(['Total Liabilities', balance_sheet_data['liabilities']])

    # --- Write Equity ---
    writer.writerow(['Equity', ''])
    for account in ACCOUNT_CLASSIFICATIONS['Equity']:
        amount = sum(t.amount for t in transactions if t.account == account)
        writer.writerow([account, format_currency(amount, current_user.currency.symbol)])
    writer.writerow(['Total Equity', balance_sheet_data['equity']])
    # Prepare the response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=balance_sheet.csv'
    return response

@accounting_routes.route('/accounting/cash_flow_statement', methods=['GET'])
@login_required
def cash_flow_statement():
    start_date_str = request.args.get('start_date', datetime.utcnow().strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)  # Include the end date

    # --- Get the owner ---
    owner = Owner.query.filter_by(user_id=current_user.id).first()

    # --- Fetch transactions for the period ---
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all()

    # --- Calculations ---
    net_income = calculate_net_income(start_date, end_date)
    depreciation_amortisation = calculate_depreciation_amortisation(start_date, end_date)
    changes_in_operating_assets_liabilities = calculate_changes_in_operating_assets_liabilities(start_date, end_date)

    # Calculate cash from operations using the fetched transactions
    cash_from_operations = calculate_cash_from_operations(transactions, start_date, end_date)  
    changes_in_operating_assets_liabilities = calculate_changes_in_operating_assets_liabilities(start_date, end_date) 
    cash_from_operations = calculate_cash_from_operations(transactions, start_date, end_date)

    investing_activities = calculate_investing_activities(start_date, end_date)
    # cash_from_investing = sum(item['amount'] for item in investing_activities)
    cash_from_investing = sum(float(item['amount']) for item in investing_activities if item['amount'].isdigit())

    cash_from_investing = 0
    for item in investing_activities:
        try:
            cash_from_investing += float(item['amount'])
        except ValueError:
            # Handle non-numeric values (e.g., log an error or skip the item)
            pass

    financing_activities = calculate_financing_activities(start_date, end_date)
    # cash_from_financing = sum(item['amount'] for item in financing_activities)
    cash_from_financing = sum(float(item['amount']) for item in financing_activities if item['amount'].isdigit())

    # Recalculate net cash flow with the updated cash_from_operations
    net_cash_flow = cash_from_operations + cash_from_investing + cash_from_financing

    # --- Prepare the context for the template ---
    currency_symbol = current_user.currency.symbol if current_user and current_user.currency else '$'
    cash_flow_statement_data = {
        'net_income': format_currency(net_income, currency_symbol),
        'depreciation_amortisation': format_currency(depreciation_amortisation, currency_symbol),
        'changes_in_operating_assets_liabilities': changes_in_operating_assets_liabilities,
        'cash_from_operations': format_currency(cash_from_operations, currency_symbol),
        'investing_activities': investing_activities,
        'cash_from_investing': format_currency(cash_from_investing, currency_symbol),
        'financing_activities': financing_activities,
        'cash_from_financing': format_currency(cash_from_financing, currency_symbol),
        'net_cash_flow': format_currency(net_cash_flow, currency_symbol),
        'currency_symbol': currency_symbol,
    }

    return render_template('accounting/cash_flow_statement.html', cash_flow_statement=cash_flow_statement_data, datetime=datetime)

@accounting_routes.route('/accounting/financials', methods=['GET'])
@login_required
def financials():
    start_date_str = request.args.get('start_date', datetime.utcnow().strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)  # Include the end date

    # --- Get the owner and properties ---
    owner = Owner.query.options(joinedload(Owner.user)).filter_by(user_id=current_user.id).first()
    properties = Property.query.filter_by(owner_id=owner.id).all() if owner else []

    # --- Calculations ---
    total_assets = calculate_total_assets(start_date, end_date) 
    net_income = calculate_net_income(start_date, end_date)  
    cash_flow = calculate_net_cash_flow(start_date, end_date)  

    # --- Get the currency symbol ---
    # currency_symbol = current_user.currency.symbol if current_user and current_user.currency else '$'
    user = User.query.options(joinedload(User.currency)).get(current_user.id) 
    currency_symbol = user.currency.symbol if user and user.currency else '$' 

    return render_template(
        'accounting/financials.html',
        total_assets=total_assets, 
        net_income=net_income,  
        cash_flow=cash_flow,
        properties=properties,
        start_date=start_date_str,
        end_date=end_date_str,
        datetime=datetime,
        currency_symbol=currency_symbol
    )


def calculate_retained_earnings(transactions):
    """
    Calculates retained earnings based on transactions.
    This is a placeholder - you'll need to implement your actual logic.

    This might involve:
      - Getting the beginning balance of retained earnings.
      - Adding net income (from the income statement).
      - Subtracting dividends.
    """
    # Placeholder implementation:
    net_income = sum(transaction.amount for transaction in transactions if transaction.main_category == 'Revenue') - \
                 sum(transaction.amount for transaction in transactions if transaction.main_category == 'Expenses')
    dividends = sum(transaction.amount for transaction in transactions if transaction.account == 'Distributions')
    return net_income - dividends 

def generate_income_statement_data():
    # This function should return the income statement data
    transactions = db.session.query(Transaction).filter(Transaction.is_reconciled == True).all()
    
    # Calculations
    revenue = sum(transaction.amount for transaction in transactions if transaction.main_category == 'Revenue')
    cost_of_sales = sum(transaction.amount for transaction in transactions if transaction.sub_category == 'Cost of Sales')
    gross_income = revenue - cost_of_sales

    overhead_expenses = sum(transaction.amount for transaction in transactions if transaction.main_category == 'Expenses' and transaction.sub_category != 'Cost of Sales')
    net_income = gross_income - overhead_expenses

    # Prepare the income statement data
    income_statement_data = {
        'income': revenue,
        'cost_of_sales': cost_of_sales,
        'gross_income': gross_income,
        'overhead_expenses': overhead_expenses,
        'net_income': net_income,
        'revenue_categories': {},  
        'expense_categories': {}   
    }

    # Populate revenue categories
    revenue_categories = {
        'Rental Income': 0,
        'Other Income': 0
    }
    
    for transaction in transactions:
        if transaction.main_category == 'Expenses' and transaction.sub_category != 'Cost of Sales':

            if transaction.sub_category in revenue_categories:
                revenue_categories[transaction.sub_category] += transaction.amount

    income_statement_data['revenue_categories'] = revenue_categories

    # Populate expense categories
    expense_categories = {}
    for transaction in transactions:
        if transaction.main_category == 'Expenses':
            category = transaction.sub_category
            expense_categories.setdefault(category, 0)
            expense_categories[category] += transaction.amount

    income_statement_data['expense_categories'] = expense_categories

    return income_statement_data

def format_currency(amount, currency_symbol):
    return f"{currency_symbol}{amount:,.2f}"

def generate_balance_sheet_data(start_date, end_date):
    """
    Generates the balance sheet data.
    """
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date + timedelta(days=1)  # Include end_date
    ).all()


    # Assets
    assets = sum(transaction.amount for transaction in transactions if transaction.main_category == 'Assets')
    current_assets = sum(transaction.amount for transaction in transactions if transaction.sub_category == 'Current Assets')
    non_current_assets = sum(transaction.amount for transaction in transactions if transaction.sub_category == 'Non-Current Assets')
    cash_cash_equivalents = sum(transaction.amount for transaction in transactions if transaction.account == 'Bank')  

    accounts_receivable = sum(transaction.amount for transaction in transactions if transaction.account in (
        'Accounts Receivable', 'Prepaid Expenses', 'Prepaid Insurance', 'Prepaid Rent'
    ))
    property_plant_equipment = sum(transaction.amount for transaction in transactions if transaction.account in (
        'Building', 'Equipment', 'Furniture and Fixtures', 'Land'
    ))

    # Liabilities
    liabilities = sum(transaction.amount for transaction in transactions if transaction.main_category == 'Liabilities')
    current_liabilities = sum(transaction.amount for transaction in transactions if transaction.sub_category == 'Current Liabilities')
    non_current_liabilities = sum(transaction.amount for transaction in transactions if transaction.sub_category == 'Non-Current Liabilities')
    accounts_payable = sum(transaction.amount for t in transactions if t.account == 'Accounts Payable') 
    mortgage_payable = sum(transaction.amount for t in transactions if t.account == 'Mortgage Payable')

    # Equity 
    equity = sum(transaction.amount for t in transactions if t.main_category == 'Equity')
    share_capital = sum(t.amount for t in transactions if t.account in (
        'Contributed Capital', 'Owner/s Capital', 'Partner Contributions'
    ))
    dividends = sum(t.amount for t in transactions if t.account == 'Distributions')

    # You'll need a function to calculate retained earnings (replace this)
    retained_earnings = calculate_retained_earnings(transactions)  

    liabilities_equity = liabilities + equity

    # --- Prepare the data dictionary ---
    balance_sheet_data = {
        'assets': format_currency(assets, current_user.currency.symbol),
        'current_assets': format_currency(current_assets, current_user.currency.symbol),
        'non_current_assets': format_currency(non_current_assets, current_user.currency.symbol),
        'cash_cash_equivalents': format_currency(cash_cash_equivalents, current_user.currency.symbol),
        'accounts_receivable': format_currency(accounts_receivable, current_user.currency.symbol),
        'property_plant_equipment': format_currency(property_plant_equipment, current_user.currency.symbol),

        'liabilities': format_currency(liabilities, current_user.currency.symbol),
        'current_liabilities': format_currency(current_liabilities, current_user.currency.symbol),
        'non_current_liabilities': format_currency(non_current_liabilities, current_user.currency.symbol),
        'accounts_payable': format_currency(accounts_payable, current_user.currency.symbol),
        'mortgage_payable': format_currency(mortgage_payable, current_user.currency.symbol),

        'equity': format_currency(equity, current_user.currency.symbol),
        'share_capital': format_currency(share_capital, current_user.currency.symbol),
        'dividends': format_currency(dividends, current_user.currency.symbol),
        'retained_earnings': format_currency(retained_earnings, current_user.currency.symbol), 
        'liabilities_equity': format_currency(liabilities_equity, current_user.currency.symbol), 
        'currency_symbol': current_user.currency.symbol,
    }

    return balance_sheet_data

def calculate_cash_from_operations(transactions, start_date, end_date):
    """
    Calculates cash flow from operating activities.
    """
    operating_transactions = []

    # Include revenue transactions
    for account in ACCOUNT_CLASSIFICATIONS['Revenue']['Rental Income']:
        operating_transactions.extend([t for t in transactions if t.account == account and t.is_reconciled == True])
    for account in ACCOUNT_CLASSIFICATIONS['Revenue']['Other Income']:
        operating_transactions.extend([t for t in transactions if t.account == account and t.is_reconciled == True])

    # Deduct expense transactions
    for category, accounts in ACCOUNT_CLASSIFICATIONS['Expenses'].items():
        for account in accounts:
            operating_transactions.extend([t for t in transactions if t.account == account and t.amount < 0 and t.is_reconciled == True])

    changes_in_operating_assets_liabilities = calculate_changes_in_operating_assets_liabilities(start_date, end_date)  

    # Calculate net cash from operating activities
    net_cash_from_operating_activities = (
        sum(t.amount for t in operating_transactions)
        + sum(item['amount'] for item in changes_in_operating_assets_liabilities)
    )

    return net_cash_from_operating_activities

def calculate_cash_from_investing(transactions):
    """
    Calculates cash flow from investing activities.
    """
    investing_transactions = []
    for account in ACCOUNT_CLASSIFICATIONS['Assets']['Non-Current Assets']:
        investing_transactions.extend([t for t in transactions if t.account == account])

    net_cash_from_investing_activities = sum(t.amount for t in investing_transactions)

    return net_cash_from_investing_activities


def calculate_cash_from_financing(transactions):
    """
    Calculates cash flow from financing activities.
    """

    financing_transactions = []
    for account in ACCOUNT_CLASSIFICATIONS['Liabilities']['Current Liabilities']:
        financing_transactions.extend([t for t in transactions if t.account == account])
    for account in ACCOUNT_CLASSIFICATIONS['Liabilities']['Non-Current Liabilities']:
        financing_transactions.extend([t for t in transactions if t.account == account])
    for account in ACCOUNT_CLASSIFICATIONS['Equity']:
        financing_transactions.extend([t for t in transactions if t.account == account])

    net_cash_from_financing_activities = sum(t.amount for t in financing_transactions)

    return net_cash_from_financing_activities

def calculate_investing_activities(start_date, end_date):
    """Calculates cash flow from investing activities."""
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all()

    activities = []
    # Example investing activities (replace with your actual accounts)
    accounts_to_check = {
        "Purchase of Property": "Purchase of Property, Plant, and Equipment",
        "Sale of Property": "Proceeds from Sale of Property, Plant, and Equipment",
    }
    for account, label in accounts_to_check.items():
        amount = sum(t.amount for t in transactions if t.account == account)
        activities.append({'label': label, 'amount': format_currency(amount, current_user.currency.symbol)})

    return activities


def calculate_financing_activities(start_date, end_date):
    """Calculates cash flow from financing activities."""
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all()

    activities = []
    # Example financing activities (replace with your actual accounts)
    accounts_to_check = {
        "Loan Received": "Proceeds from Issuance of Debt",
        "Loan Repayment": "Repayment of Debt",
        "Owner's Capital": "Proceeds from Issuance of Stock",  # Assuming this is equivalent to stock issuance
        "Distributions": "Payment of Dividends",
    }
    for account, label in accounts_to_check.items():
        amount = sum(t.amount for t in transactions if t.account == account)
        activities.append({'label': label, 'amount': format_currency(amount, current_user.currency.symbol)})

    return activities

def calculate_total_assets(start_date, end_date):
    """Calculates total assets from the balance sheet."""
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,  
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all()

    assets = 0
    for category, accounts in ACCOUNT_CLASSIFICATIONS['Assets'].items():
        for account in accounts:
            assets += sum(t.amount for t in transactions if t.account == account)

    return assets

def calculate_net_income(start_date, end_date):
    """Calculates net income from the income statement."""
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all()

    revenue = sum(t.amount for t in transactions if t.main_category == 'Revenue')
    
    # Calculate total tax on rental income
    total_rental_income_tax = 0
    for t in transactions:
        if t.main_category == 'Revenue':
            property = Property.query.get(t.property_id)
            if property and property.rental_income_tax_rate:
                tax_rate = property.rental_income_tax_rate / 100  # Convert to decimal
                total_rental_income_tax += t.amount * tax_rate

    revenue_after_tax = revenue - total_rental_income_tax  

    cost_of_sales = sum(t.amount for t in transactions if t.sub_category == 'Cost of Sales')
    gross_income = revenue_after_tax - cost_of_sales  # Use revenue after tax
    overhead_expenses = sum(t.amount for t in transactions if t.main_category == 'Expenses' and t.sub_category != 'Cost of Sales')
    net_income = gross_income - overhead_expenses

    return net_income


def calculate_net_cash_flow(start_date, end_date):
    """Calculates net cash flow from the cash flow statement."""
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all()

    depreciation_amortisation = calculate_depreciation_amortisation(start_date, end_date)

    return (
        calculate_cash_from_operations(transactions, start_date, end_date)  # Pass start_date and end_date here
        + calculate_cash_from_investing(transactions)
        + calculate_cash_from_financing(transactions)
        + depreciation_amortisation
    )

def calculate_depreciation_amortisation(start_date, end_date):
    """Calculates depreciation and amortization."""
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all()

    depreciation_amortisation = 0
    for category, accounts in ACCOUNT_CLASSIFICATIONS['Expenses'].items():
        if category == 'Depreciation & Amortization':  # Check if the category is Depreciation & Amortization
            for account in accounts:
                depreciation_amortisation += sum(t.amount for t in transactions if t.account == account and t.amount < 0)

    return depreciation_amortisation

def calculate_changes_in_operating_assets_liabilities(start_date, end_date):
    """Calculates changes in operating assets and liabilities."""
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date < end_date
    ).all()

    # changes_in_operating_assets_liabilities = calculate_changes_in_operating_assets_liabilities(start_date, end_date)

    changes = []
    accounts_to_check = {
        "Accounts Receivable": "Increase (Decrease) in Accounts Receivable",
        "Prepaid Rent": "Increase (Decrease) in Prepaid Rent",
        "Accounts Payable": "Increase (Decrease) in Accounts Payable",
        "Accrued Expenses": "Increase (Decrease) in Accrued Expenses",
    }

    for account, label in accounts_to_check.items():
        beginning_balance = calculate_beginning_balance(account, start_date)
        ending_balance = calculate_ending_balance(account, end_date)
        change = ending_balance - beginning_balance
        changes.append({'label': label, 'amount': change}) 

    return changes


def calculate_beginning_balance(account, start_date):
    """Calculates the beginning balance of an account."""
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.account == account,
        Transaction.transaction_date < start_date
    ).all()
    return sum(t.amount for t in transactions)

def calculate_ending_balance(account, end_date):
    """Calculates the ending balance of an account."""
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter(
        Transaction.owner_id == owner.id,
        Transaction.is_reconciled == True,
        Transaction.account == account,
        Transaction.transaction_date < end_date
    ).all()
    return sum(t.amount for t in transactions)

def calculate_property_tax(property):
    """Calculates property tax for a given property."""

    if property.tax_assessed_value and property.tax_rate:
        assessed_value = property.tax_assessed_value
        tax_rate = property.tax_rate / 100  
    else:
        # Fetch from external API using property_id
        tax_data = get_property_tax(property_id=property.id)  # Pass property_id as a keyword argument
        
        # Validate API response and extract data
        if not isinstance(tax_data, dict) or 'result' not in tax_data:
            app.logger.error(f"Unexpected API response format: {tax_data}")
            raise ValueError("Invalid data received from the API.")  # Raise an exception to handle the error

        assessed_value = tax_data['result'].get('assessed_value')
        tax_rate = tax_data['result'].get('tax_rate') / 100  # Assuming tax_rate is a percentage

        if assessed_value is None or tax_rate is None:
            app.logger.error(f"Missing assessed_value or tax_rate in API response: {tax_data}")
            raise ValueError("Missing required data in API response.")

    if property.tax_assessed_value and property.tax_rate:
        assessed_value = property.tax_assessed_value
        tax_rate = property.tax_rate / 100  
    else:
        # Fetch from external API (replace with your API call)
        tax_data = get_property_tax(property.street_address, property.city, property.state_id) 
        assessed_value = tax_data['assessed_value']
        tax_rate = tax_data['tax_rate']

    tax_amount = assessed_value * tax_rate

    transaction = Transaction(
        transaction_date=datetime.now(), 
        amount=tax_amount,  
        description="Property Tax Payment",
        main_category="Expenses",
        sub_category="Taxes",
        account="Property Taxes",
        is_property_tax=True,
        property_id=property.id,
        owner_id=property.owner_id
    )
    db.session.add(transaction)
    db.session.commit()

    return tax_amount

@accounting_routes.route('/property_tax', methods=['GET'])
def get_property_tax():
    property_id = request.args.get('property_id')

    if not property_id:
        return jsonify({"error": "Missing required parameter: property_id"}), 400

    try:
        property = Property.query.get(property_id)
        if not property:
            return jsonify({"error": "Property not found"}), 404

        params = {
            'state': property.state.state if property.state else None, 
            'city': property.city, 
            'address1': property.street_address,  # Use 'address1'
            'zip': property.zip_code  
        }

        params = {k: v for k, v in params.items() if v is not None}

        response = requests.get(
            app.config['API_NINJA_API_URL'],
            params=params,
            headers={'X-Api-Key': app.config['API_NINJA_API_KEY']}
        )
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict) or 'result' not in data:
            app.logger.error(f"Unexpected API response format: {data}")
            return jsonify({"error": "Invalid data received from the API."}), 500

        return jsonify(data)

    except requests.exceptions.HTTPError as e:
        app.logger.error(f"API request failed with HTTP error: {e}")
        return jsonify({"error": "Failed to fetch property tax data. Please check your input and try again."}), e.response.status_code
    except requests.exceptions.RequestException as e:
        app.logger.error(f"API request failed: {e}")
        return jsonify({"error": "An error occurred while processing your request. Please try again later."}), 500

def generate_invoice_pdf(invoice_data):
    # Generate HTML content for the invoice
    html_content = render_template('invoice.html', invoice=invoice_data)
    
    # Configure pdfkit to use wkhtmltopdf wrapper script
    config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf.sh')
    
    # Generate PDF from HTML
    pdfkit.from_string(
        html_content,
        'invoice.pdf',
        configuration=config,
        css='static/css/invoice.css'
    )
