from venv import logger
from flask import Blueprint, g, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Transaction, Property, Owner
from forms import TransactionForm
from app_constants import ACCOUNT_CLASSIFICATIONS, GAAPClassifier, ACCOUNTS

# Create a blueprint for accounting routes if not already existing
transaction_routes = Blueprint('transaction_routes', __name__, url_prefix='/transactions')

def get_account_classifications():
    """Return account classifications."""
    return ACCOUNT_CLASSIFICATIONS

def get_debit_credit_amount(account_name: str, amount: float) -> float:
    """
    Determines if an amount should be credited (negative) or debited (positive)
    based on the account's GAAP classification.
    
    Args:
        account_name: The name of the account
        amount: The original amount (positive number)
        
    Returns:
        float: Positive number for debit, negative number for credit
    """
    # Get the account's classification (Assets, Liabilities, etc.)
    if account_name not in ACCOUNTS:
        raise ValueError(f"Unknown account: {account_name}")
        
    classification = ACCOUNTS[account_name][0]  # First element is the classification
    
    # Get the normal balance for this classification (Debit or Credit)
    normal_balance = GAAPClassifier.CLASSIFICATION[classification]
    
    # If normal balance is Credit, make the amount negative
    return amount if normal_balance == "Debit" else -amount

def get_main_category_from_sub_category(sub_category):
    """Determine the main category based on the sub category."""
    main_category_map = {
        'Current Asset': 'Assets',
        'Non-Current Asset': 'Assets',
        'Current Liability': 'Liabilities',
        'Non-Current Liability': 'Liabilities',
        'Equity': 'Equity',
        'Revenue': 'Revenue',
        'Operating Expenses': 'Expenses',
        'Common Area Expenses': 'Expenses',
        'Occupancy Expenses': 'Expenses',
        'Financial Expenses': 'Expenses',
        'Miscellaneous': 'Miscellaneous'
    }
    
    # Retrieve the main category for the given sub category, defaulting to 'Miscellaneous' if not found
    main_category = main_category_map.get(sub_category, 'Miscellaneous')
    if main_category == 'Miscellaneous':
        current_app.logger.warning(f"Unrecognized sub category: {sub_category}, defaulting to 'Miscellaneous'")
    
    return main_category

def get_sub_category_from_account(account):
    """Determine the sub category based on the account type using ACCOUNT_CLASSIFICATIONS."""
    sub_category_map = {}

    if account == 'Accounts Receivable':
        return 'Current Asset'
    
    elif account == 'Building':
        return 'Non-Current Asset'
    
    elif account == 'Equipment':
        return 'Non-Current Asset'
    
    elif account == 'Furniture and Fixtures':
        return 'Non-Current Asset'
    
    elif account == 'Land':
        return 'Non-Current Asset'
    
    elif account == 'Leasehold Improvements':
        return 'Non-Current Asset'
    
    elif account == 'Prepaid Expenses':
        return 'Current Asset'
    
    elif account == 'Prepaid Insurance':
        return 'Current Asset' 
    
    elif account == 'Prepaid Rent':
        return 'Current Asset'
    
    elif account == 'Property, Plant, and Equipment':
        return 'Non-Current Asset'
    
    elif account == 'Accounts Payable':
        return 'Current Liability'
    
    elif account == 'Accrued Expenses':
        return 'Current Liability'
    
    elif account == 'Deferred Revenue':
        return 'Current Liability'
    
    elif account == 'Long-Term Debt':
        return 'Non-Current Liability'

    elif account == 'Maintenance Reserves':
        return 'Current Liability'
    
    elif account == 'Mortgage Payable':
        return 'Non-Current Liability'
    
    elif account == 'Prepaid Rent':
        return 'Current Liability'
    
    elif account == 'Property Tax Payable':
        return 'Current Liability'
    
    elif account == 'Security Deposits':
        return 'Current Liability'
    
    elif account == 'Unearned Rent':
        return 'Current Liability'
    
    elif account == 'Contributed Capital':
        return 'Equity'
    
    elif account == 'Current Year Earnings':
        return 'Equity'
    
    elif account == 'Distributions':
        return 'Equity'
    
    elif account == 'Owner\'s Capital':
        return 'Equity'
    
    elif account == 'Owner\'s Withdrawals':
        return 'Equity'
    
    elif account == 'Partner Contributions':
        return 'Equity'
    
    elif account == 'Retained Earnings':
        return 'Equity'
    
    elif account == 'Retained Earnings (Accumulated)':
        return 'Equity'
    
    elif account == 'Retained Earnings (Current Year)':
        return 'Equity'
    
    elif account == 'Application Fees':
        return 'Income'
    
    elif account == 'Common Area Revenue':
        return 'Income'
    
    elif account == 'Late Fee Income':
        return 'Income'
    
    elif account == 'Other Revenue':
        return 'Income'
    
    elif account == 'Parking Fees':
        return 'Income'
    
    elif account == 'Pet Rent':
        return 'Income'
    
    elif account == 'Rental Income':
        return 'Income'
    
    elif account == 'Storage Unit Rental':
        return 'Income'
    
    elif account == 'Utility Reimbursements':
        return 'Income'
    
    elif account == 'Administrative Expenses':
        return 'Operating Expenses'
    
    elif account == 'Insurance':
        return 'Operating Expenses'
    
    elif account == 'Legal and Professional Fees':
        return 'Operating Expenses'
    
    elif account == 'Maintenance and Repairs':
        return 'Operating Expenses'
    
    elif account == 'Marketing and Advertising':
        return 'Operating Expenses'
    
    elif account == 'Pest Control':
        return 'Operating Expenses'
    
    elif account == 'Property Management Fees':
        return 'Operating Expenses'
    
    elif account == 'Property Taxes':
        return 'Operating Expenses'
    
    elif account == 'Security Services':
        return 'Operating Expenses'
    
    elif account == 'Utilities':
        return 'Operating Expenses'
    
    elif account == 'Common Area Maintenance (CAM)':
        return 'Common Area Expenses'
    
    elif account == 'Common Area Utilities':
        return 'Common Area Expenses'
    
    elif account == 'Landscaping':
        return 'Common Area Expenses'
    
    elif account == 'Lighting':
        return 'Common Area Expenses'
    
    elif account == 'Lobby Maintenance':
        return 'Common Area Expenses'
    
    elif account == 'Parking Lot Maintenance':
        return 'Common Area Expenses'
    
    elif account == 'Security Systems':
        return 'Common Area Expenses'
    
    elif account == 'Signage':
        return 'Common Area Expenses'
    
    elif account == 'Snow Removal':
        return 'Common Area Expenses'
    
    elif account == 'Cleaning Services':
        return 'Occupancy Expenses'
    
    elif account == 'Elevator Maintenance':
        return 'Occupancy Expenses'
    
    elif account == 'Maintenance and Repairs':
        return 'Occupancy Expenses'
    
    elif account == 'Lease Payments':
        return 'Occupancy Expenses'
    
    elif account == 'Rent':
        return 'Occupancy Expenses'
    
    elif account == 'Tenant Improvements':
        return 'Occupancy Expenses'
    
    elif account == 'Waste Management':
        return 'Occupancy Expenses'
    
    elif account == 'Bank Fees':
        return 'Financial Expenses'
    
    elif account == 'Credit Card Processing Fees':
        return 'Financial Expenses' 
    
    elif account == 'Late Payment Penalties':
        return 'Financial Expenses'
    
    elif account == 'Loan Processing Fees':
        return 'Financial Expenses'
    
    elif account == 'Mortgage Interest':
        return 'Financial Expenses'
    
    elif account == 'Property Insurance':
        return 'Financial Expenses'
    
    elif account == 'Property Tax Assessments':
        return 'Financial Expenses'
    
    # Retrieve the sub-category for the given account, defaulting to 'Miscellaneous' if not found
    sub_category = sub_category_map.get(account, 'Miscellaneous')
    if sub_category == 'Miscellaneous':
        current_app.logger.warning(f"Unrecognized account type: {account}, defaulting to 'Miscellaneous'")
    
    return sub_category

def get_main_category_from_account(account):
    """Determine the main category based on the account type."""
    # Account to main category mapping
    account_category_map = {
        # Asset accounts
        'Accounts Receivable': 'Assets',
        'Building': 'Assets',
        'Equipment': 'Assets',
        'Furniture and Fixtures': 'Assets',
        'Land': 'Assets',
        'Leasehold Improvements': 'Assets',
        'Prepaid Expenses': 'Assets',
        'Prepaid Insurance': 'Assets',
        'Prepaid Rent': 'Assets',
        'Property, Plant, and Equipment': 'Assets',
        
        # Liability accounts
        'Accounts Payable': 'Liabilities',
        'Accrued Expenses': 'Liabilities',
        'Deferred Revenue': 'Liabilities',
        'Long-Term Debt': 'Liabilities',
        'Maintenance Reserves': 'Liabilities',
        'Mortgage Payable': 'Liabilities',
        'Property Tax Payable': 'Liabilities',
        'Security Deposits': 'Liabilities',
        'Unearned Rent': 'Liabilities',
        
        # Equity accounts
        'Contributed Capital': 'Equity',
        'Current Year Earnings': 'Equity',
        'Distributions': 'Equity',
        "Owner's Capital": 'Equity',
        "Owner's Withdrawals": 'Equity',
        'Partner Contributions': 'Equity',
        'Retained Earnings': 'Equity',
        
        # Revenue accounts
        'Application Fees': 'Revenue',
        'Common Area Revenue': 'Revenue',
        'Late Fee Income': 'Revenue',
        'Other Revenue': 'Revenue',
        'Parking Fees': 'Revenue',
        'Pet Rent': 'Revenue',
        'Rental Income': 'Revenue',
        'Storage Unit Rental': 'Revenue',
        'Utility Reimbursements': 'Revenue',
        
        # Expense accounts
        'Administrative Expenses': 'Expenses',
        'Insurance': 'Expenses',
        'Legal and Professional Fees': 'Expenses',
        'Maintenance and Repairs': 'Expenses',
        'Marketing and Advertising': 'Expenses',
        'Pest Control': 'Expenses',
        'Property Management Fees': 'Expenses',
        'Property Taxes': 'Expenses',
        'Security Services': 'Expenses',
        'Utilities': 'Expenses',
        'Common Area Maintenance (CAM)': 'Expenses',
        'Landscaping': 'Expenses',
        'Cleaning Services': 'Expenses',
        'Bank Fees': 'Expenses',
        'Mortgage Interest': 'Expenses',
        'Property Insurance': 'Expenses'
    }
    
    # Get the main category for the given account, defaulting to 'Miscellaneous' if not found
    main_category = account_category_map.get(account)
    if not main_category:
        current_app.logger.warning(f"Unrecognized account: {account}, defaulting to 'Miscellaneous'")
        return 'Miscellaneous'
    
    return main_category

@transaction_routes.route('/overview', methods=['GET'])
@login_required
def transactions():
    # Create form instance
    form = TransactionForm()
    
    # Get page number from request args, default to 1
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of items per page

    # Get owner information
    owner = Owner.query.filter_by(user_id=current_user.id).first()
    
    # Get properties
    properties = Property.query.filter_by(owner_id=owner.id).all() if owner else []
    
    # Get paginated transactions
    transactions_pagination = Transaction.query.order_by(
        Transaction.transaction_date.desc()
    ).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )

    # Get account classifications
    account_classifications = get_account_classifications()

    return render_template(
        'transaction/transactions.html',
        form=form,
        transactions=transactions_pagination.items,
        properties=properties,
        page=page,
        total_pages=transactions_pagination.pages,
        total=transactions_pagination.total,
        account_classifications=account_classifications,
        current_date=datetime.utcnow()
    )

@transaction_routes.route('/save', methods=['POST'])
@login_required
def transactions_save():
    """Handle the creation and updating of transactions."""
    current_app.logger.info("=== Starting transaction save ===")

    # Log the incoming request data
    current_app.logger.debug(f"Form data: {request.form.to_dict()}")
    current_app.logger.debug(f"Headers: {dict(request.headers)}")

    try:
        # Get owner information
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            current_app.logger.error(f"Owner not found for user_id: {current_user.id}")
            flash('Owner not found', 'error')
            return redirect(url_for('transaction_routes.transactions'))

        current_app.logger.debug(f"Owner found: {owner.id}")

        action = request.form.get('action', '')
        current_app.logger.info(f"Processing action: {action}")

        if not action:
            current_app.logger.error("No action specified in form data")
            flash('No action specified', 'error')
            return redirect(url_for('transaction_routes.transactions'))

        if action == 'save_new':
            # Handle new transaction creation
            processed_date_str = request.form.get('processed_date')
            current_app.logger.debug(f"Received processed date: {processed_date_str}")

            try:
                transaction_date = datetime.strptime(processed_date_str, '%Y-%m-%d').date() if processed_date_str else None
                current_app.logger.debug(f"Parsed transaction date: {transaction_date}")
            except (ValueError, TypeError) as e:
                current_app.logger.error(f"Date parsing error: {str(e)}")
                flash('Invalid date format. Please use YYYY-MM-DD', 'error')
                return redirect(url_for('transaction_routes.transactions'))

            property_id = request.form.get('new_property_id') or None
            if property_id:
                property_id = int(property_id)

            account = request.form.get('new_account')
            description = request.form.get('new_description')
            amount = float(request.form.get('new_amount', 0))
            is_reconciled = 'new_is_reconciled' in request.form

            current_app.logger.debug(f"""
                Parsed transaction values:
                - Date: {transaction_date}
                - Property ID: {property_id}
                - Account: {account}
                - Description: {description}
                - Amount: {amount}
                - Is Reconciled: {is_reconciled}
            """)

            try:
                # Determine categories
                sub_category = get_sub_category_from_account(account)
                main_category = get_main_category_from_sub_category(sub_category)
                
                current_app.logger.debug(f"Determined categories - Main: {main_category}, Sub: {sub_category}")

                # Create new transaction
                new_transaction = Transaction(
                    transaction_date=transaction_date,
                    property_id=property_id,
                    account=account,
                    description=description,
                    amount=amount,
                    is_reconciled=is_reconciled,
                    owner_id=owner.id,
                    main_category=main_category,
                    sub_category=sub_category
                )

                db.session.add(new_transaction)
                current_app.logger.debug("Added new transaction to session")

                db.session.commit()
                current_app.logger.debug("Successfully committed new transaction")

                flash('New transaction added successfully', 'success')

            except ValueError as e:
                current_app.logger.error(f"Category determination error: {str(e)}")
                flash(f'Error determining categories: {str(e)}', 'error')
                db.session.rollback()
            except Exception as e:
                current_app.logger.error(f"Unexpected error during save_new: {str(e)}", exc_info=True)
                flash(f'An unexpected error occurred: {str(e)}', 'error')
                db.session.rollback()

        elif action.startswith('save_'):
            # Handle existing transaction update
            try:
                transaction_id = int(action.split('_')[1])
                transaction = Transaction.query.get(transaction_id)
                if not transaction or transaction.owner_id != owner.id:
                    flash('Transaction not found or access denied', 'error')
                    return redirect(url_for('transaction_routes.transactions'))

                transaction_date_str = request.form.get(f'transaction_date_{transaction_id}')
                if transaction_date_str:
                    transaction.transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
                else:
                    transaction.transaction_date = None

                property_id = request.form.get(f'property_id_{transaction_id}') or None
                if property_id:
                    property_id = int(property_id)
                transaction.property_id = property_id
                transaction.account = request.form.get(f'account_{transaction_id}')
                transaction.description = request.form.get(f'description_{transaction_id}')
                transaction.amount = float(request.form.get(f'amount_{transaction_id}', 0))
                transaction.is_reconciled = f'is_reconciled_{transaction_id}' in request.form
                transaction.last_modified = datetime.utcnow()

                db.session.commit()
                flash('Transaction updated successfully', 'success')
                current_app.logger.debug(f"Updated transaction {transaction_id}: {transaction}")

            except Exception as e:
                current_app.logger.error(f"Error updating transaction: {str(e)}", exc_info=True)
                db.session.rollback()
                flash('Error updating transaction', 'error')

        elif action.startswith('delete_'):
            # Handle transaction deletion
            try:
                transaction_id = int(action.split('_')[1])
                transaction = Transaction.query.get(transaction_id)
                if not transaction or transaction.owner_id != owner.id:
                    flash('Transaction not found or access denied', 'error')
                    return redirect(url_for('transaction_routes.transactions'))

                db.session.delete(transaction)
                db.session.commit()
                flash('Transaction deleted successfully', 'success')
                current_app.logger.debug(f"Deleted transaction {transaction_id}")

            except Exception as e:
                current_app.logger.error(f"Error deleting transaction: {str(e)}", exc_info=True)
                db.session.rollback()
                flash('Error deleting transaction', 'error')

        else:
            flash('Invalid action', 'error')

    except Exception as e:
        current_app.logger.exception(f"Exception in transactions_save: {str(e)}")
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        current_app.logger.info("=== Ending transaction save ===")

    return redirect(url_for('transaction_routes.transactions'))


def save_transaction(transaction_data):
    """Helper function to save a transaction to the database."""
    try:
        account = transaction_data.get('account')
        # Determine sub_category first
        sub_category = get_sub_category_from_account(account)
        main_category = get_main_category_from_sub_category(sub_category)

        current_app.logger.debug(
            f"Saving transaction with account: {account}, main_category: {main_category}, sub_category: {sub_category}"
        )

        # Include both categories in your transaction insert
        transaction = Transaction(
            account=account,
            main_category=main_category,
            sub_category=sub_category,
            # ... other fields from transaction_data ...
        )
        db.session.add(transaction)
        db.session.commit()

    except ValueError as e:
        current_app.logger.error(f"Error determining categories: {str(e)}")
        db.session.rollback()
        raise
    except Exception as e:
        current_app.logger.error(f"Error saving transaction: {str(e)}", exc_info=True)
        db.session.rollback()
        raise
