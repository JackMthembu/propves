import os
import re
from venv import logger
from flask import Blueprint, g, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Transaction, Property, Owner
from forms import TransactionForm
from app_constants import ACCOUNT_CLASSIFICATIONS, GAAPClassifier, ACCOUNTS
from werkzeug.utils import secure_filename
from openai import classify_transaction_with_azure
from utils import allowed_file

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


def get_sub_category_from_account(account):
    """Determine the sub-category based on the account type using ACCOUNT_CLASSIFICATIONS."""

    for main_category, sub_categories in ACCOUNT_CLASSIFICATIONS.items():
        if isinstance(sub_categories, dict):
            for sub_category, accounts in sub_categories.items():
                if account in accounts:
                    return sub_category
        elif account in sub_categories:
            return main_category
    return None

def get_main_category_from_sub_category(sub_category):
    """Determine the main category based on the sub-category."""
    for main_category, sub_categories in ACCOUNT_CLASSIFICATIONS.items():
        if isinstance(sub_categories, dict):
            if sub_category in sub_categories:  # Check if the sub_category is a key in the nested dict
                return main_category
        elif sub_category in sub_categories:  # For non-nested categories
            return main_category
    return None

def get_owner():
    # Your logic to retrieve the owner
    # For example:
    return Owner.query.filter_by(user_id=current_user.id).first()

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
    
    # Get filter parameters from the request
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    account_filter = request.args.get('account')

    # Build the query
    query = Transaction.query

    # Apply date filters if provided
    if date_from:
        query = query.filter(Transaction.transaction_date >= date_from)
    if date_to:
        query = query.filter(Transaction.transaction_date <= date_to)

    # Apply account filter if provided
    if account_filter:
        query = query.filter(Transaction.account == account_filter)

    # Get paginated transactions
    transactions_pagination = query.order_by(
        Transaction.transaction_date.desc()
    ).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )

    # Get account classifications
    account_classifications = get_account_classifications()

    # Assuming sub_categories is defined somewhere in your code
    is_dict = isinstance(account_classifications, dict)

    # Check if there are no transactions
    no_transactions = len(transactions_pagination.items) == 0

    return render_template(
        'transaction/transactions.html',
        form=form,
        transactions=transactions_pagination.items,
        properties=properties,
        page=page,
        total_pages=transactions_pagination.pages,
        total=transactions_pagination.total,
        account_classifications=account_classifications,
        owner=owner,
        current_date=datetime.utcnow(),
        date_from=date_from,
        date_to=date_to,
        account_filter=account_filter,
        is_dict=is_dict,
        no_transactions=no_transactions  # Pass the flag to the template
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
                transaction_date = datetime.strptime(processed_date_str, '%Y-%m-%d').date() if processed_date_str else datetime.utcnow().date()
                current_app.logger.debug(f"Parsed transaction date: {transaction_date}")
            except (ValueError, TypeError) as e:
                current_app.logger.error(f"Date parsing error: {str(e)}")
                flash('Invalid date format. Please use YYYY-MM-DD', 'error')
                return redirect(url_for('transaction_routes.transactions'))

            property_id = request.form.get('new_property_id')
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

                # --- Double-Entry Accounting Logic ---
                # 1. Determine the type of the first entry (debit/credit) based on the main_category
                if main_category in ('Assets', 'Expenses'):
                    first_entry_type = 'debit'
                elif main_category in ('Liabilities', 'Equity', 'Revenue'):
                    first_entry_type = 'credit'
                else:
                    raise ValueError("Invalid main category for double-entry accounting.")

                # 2. Create the first transaction entry
                new_transaction = Transaction(
                    transaction_date=transaction_date,
                    property_id=property_id,
                    account=account,
                    description=description,
                    amount=amount if first_entry_type == 'debit' else -amount,  # Adjust sign based on entry type
                    is_reconciled=is_reconciled,
                    owner_id=owner.id,
                    main_category=main_category,
                    sub_category=sub_category
                )
                db.session.add(new_transaction)

                # 3. Get the balancing account and its categories
                balancing_account, balancing_main_category, balancing_sub_category = get_balancing_account(
                    account, main_category, amount
                )

                # 4. Determine the type of the second entry
                second_entry_type = 'credit' if first_entry_type == 'debit' else 'debit'

                # 5. Create the second transaction entry (the balancing entry)
                balancing_transaction = Transaction(
                    transaction_date=transaction_date,
                    property_id=property_id,
                    account=balancing_account,
                    description=f"Balancing entry for {description}",
                    amount=-amount if second_entry_type == 'debit' else amount,  # Adjust sign
                    is_reconciled=is_reconciled,
                    owner_id=owner.id,
                    main_category=balancing_main_category,
                    sub_category=balancing_sub_category
                )
                db.session.add(balancing_transaction)

                db.session.commit()
                flash('New transaction with double-entry added successfully', 'success')

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
                
                # Update account and determine categories
                transaction.account = request.form.get(f'account_{transaction_id}')
                
                # Determine sub_category and main_category based on the updated account
                sub_category = get_sub_category_from_account(transaction.account)
                main_category = get_main_category_from_sub_category(sub_category)
                
                # Update the transaction with the new categories
                transaction.main_category = main_category
                transaction.sub_category = sub_category
                
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
    
@transaction_routes.route('/save_all', methods=['POST'])
@login_required
def transactions_save_all():
    """Handle the creation and updating of transactions."""
    current_app.logger.info("=== Starting transaction save ===")

    try:
        # Get owner information
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            current_app.logger.error(f"Owner not found for user_id: {current_user.id}")
            flash('Owner not found', 'error')
            return redirect(url_for('transaction_routes.transactions'))

        # Process each transaction
        for transaction_id in request.form:
            if transaction_id.startswith('transaction_date_'):
                transaction_id_num = transaction_id.split('_')[1]
                transaction = Transaction.query.get(transaction_id_num)
                if transaction and transaction.owner_id == owner.id:
                    # Log the transaction details before processing
                    current_app.logger.debug(f"Processing transaction ID {transaction_id_num}")

                    # Parse the date correctly
                    transaction_date_str = request.form[transaction_id]
                    if transaction_date_str:
                        transaction.transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
                    else:
                        flash(f'Transaction ID {transaction_id_num} requires a date.', 'error')
                        continue  # Skip this transaction and continue with the next

                    transaction.property_id = request.form.get(f'property_id_{transaction_id_num}')
                    transaction.account = request.form.get(f'account_{transaction_id_num}')
                    transaction.description = request.form.get(f'description_{transaction_id_num}')
                    transaction.amount = float(request.form.get(f'amount_{transaction_id_num}', 0))
                    transaction.is_reconciled = f'is_reconciled_{transaction_id_num}' in request.form

                    # Log the transaction details after processing
                    current_app.logger.debug(f"Updated transaction ID {transaction_id_num}: {transaction}")

        db.session.commit()
        flash('All transactions updated successfully', 'success')

    except Exception as e:
        current_app.logger.error(f"Error saving transactions: {str(e)}", exc_info=True)
        db.session.rollback()
        flash('An error occurred while saving transactions', 'error')

    return redirect(url_for('transaction_routes.transactions'))


def generate_journal_entry(transaction_data):
    """
    Generates a journal entry (a list of transactions) based on the 
    provided transaction data.

    Args:
        transaction_data (dict): A dictionary containing the transaction details.
            Example:
            {
                'transaction_date': '2024-01-15',
                'description': 'Rent payment',
                'account': 'Bank',
                'amount': 1500.00,
            }

    Returns:
        list: A list of Transaction objects representing the journal entry.
    """

    try:
        # 1. Extract basic transaction details
        transaction_date = datetime.strptime(transaction_data['transaction_date'], '%Y-%m-%d').date()
        description = transaction_data['description']
        account = transaction_data['account']
        amount = transaction_data['amount']

        # 2. Determine categories
        sub_category = get_sub_category_from_account(account)
        main_category = get_main_category_from_sub_category(sub_category)

        # 3. Determine the first entry type (debit/credit)
        if main_category in ('Assets', 'Expenses'):
            first_entry_type = 'debit'
        elif main_category in ('Liabilities', 'Equity', 'Revenue'):
            first_entry_type = 'credit'
        else:
            raise ValueError("Invalid main category for double-entry accounting.")

        # 4. Create the first transaction entry
        first_entry = Transaction(
            transaction_date=transaction_date,
            description=description,
            account=account,
            amount=amount if first_entry_type == 'debit' else -amount,
            main_category=main_category,
            sub_category=sub_category,
            # ... add other fields from transaction_data ...
        )

        # 5. Get the balancing account and its categories
        balancing_account, balancing_main_category, balancing_sub_category = get_balancing_account(
            account, main_category, amount
        )

        # 6. Determine the second entry type
        second_entry_type = 'credit' if first_entry_type == 'debit' else 'debit'

        # 7. Create the second transaction entry (balancing entry)
        second_entry = Transaction(
            transaction_date=transaction_date,
            description=f"Balancing entry for {description}",
            account=balancing_account,
            amount=-amount if second_entry_type == 'debit' else amount,
            main_category=balancing_main_category,
            sub_category=balancing_sub_category,
        )

        # 8. Return the journal entry as a list of transactions
        return [first_entry, second_entry]

    except Exception as e:
        current_app.logger.error(f"Error generating journal entry: {str(e)}", exc_info=True)
        raise  # Re-raise the exception to be handled by the calling function


def get_balancing_account(account, main_category, amount):
    """
    Determines the balancing account and its categories based on 
    the provided account, main category, and amount.
    """

    if main_category == 'Assets':
        if account == 'Bank':
            # Simplified rule for Bank account:
            return ('Rental Income', 'Revenue', 'Rental Income') if amount > 0 else \
                   ('Accounts Payable', 'Liabilities', 'Current Liabilities') 

        # For all other assets, the balancing account is Bank
        return 'Bank', 'Assets', 'Current Assets'

    elif main_category in ('Liabilities', 'Equity', 'Revenue'):
        # Simplified rule for Liabilities, Equity, and Revenue:
        return 'Bank', 'Assets', 'Current Assets'

    elif main_category == 'Expenses':
        # Simplified rule for all Expenses:
        return 'Bank', 'Assets', 'Current Assets'

    else:
        raise ValueError("No balancing account rule found for this transaction.")

@transaction_routes.route('/upload', methods=['POST'])
@login_required
def upload_document():
    """
    Handles document uploads, analyzes them using the AI agent, 
    and populates the transactions table.
    """
    current_app.logger.info("=== Starting document upload ===")

    try:
        # Get owner information
        owner = Owner.query.filter_by(user_id=current_user.id).first()
        if not owner:
            current_app.logger.error(f"Owner not found for user_id: {current_user.id}")
            flash('Owner not found', 'error')
            return redirect(url_for('transaction_routes.transactions'))

        # Check if the post request has the file part
        if 'files[]' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        files = request.files.getlist('files[]')

        for file in files:
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                # Analyze the document using the AI agent
                try:
                    transactions_data = analyze_document(filepath)  # Get a list of transaction dictionaries
                    current_app.logger.debug(f"Extracted transactions: {transactions_data}")

                    # Create and save transactions
                    for transaction_data in transactions_data:
                        try:
                            journal_entry = generate_journal_entry(transaction_data)
                            for transaction in journal_entry:
                                transaction.owner_id = owner.id
                                db.session.add(transaction)
                            db.session.commit()
                        except Exception as e:
                            current_app.logger.error(f"Error saving transaction: {str(e)}")
                            db.session.rollback()
                            flash(f"Error saving transaction: {str(e)}", 'error')
                            return jsonify({'success': False, 'error': str(e)})  # Return error response

                except Exception as e:
                    current_app.logger.error(f"Error analyzing document: {str(e)}")
                    flash(f"Error analyzing document: {str(e)}", 'error')
                    return jsonify({'success': False, 'error': str(e)})  # Return error response

                flash('Document uploaded and transactions processed successfully!', 'success')
                return jsonify({'success': True})  # Return success response
   
    except Exception as e:
        current_app.logger.exception(f"Exception in upload_document: {str(e)}")
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)})

    finally:
        current_app.logger.info("=== Ending document upload ===")
        return redirect(url_for('transaction_routes.transactions'))

def analyze_document(filepath):
    """
    Analyzes the uploaded document and extracts transaction data.
    Uses Azure LLM to classify items.
    """
    extracted_transactions = []

    with open(filepath, 'r') as file:
        file_content = file.read()

    # Extract the total amount due (Example regex to find total amount)
    total_amount_due_match = re.search(r"Total Amount Due US\$([\d.]+)", file_content)
    if total_amount_due_match:
        total_amount_due = float(total_amount_due_match.group(1))
        current_app.logger.debug(f"Total amount due: {total_amount_due}")

        # Extract individual expense items and amounts
        expenses = re.findall(r"([A-Za-z\s]+) US\$([\d.]+)", file_content)
        current_app.logger.debug(f"Extracted expenses: {expenses}")

        # Create a transaction for the total amount due (debit)
        extracted_transactions.append({
            'transaction_date': '2024-10-31',  # Placeholder for transaction date
            'description': 'Payment for HOA Fees and other expenses',
            'account': 'Bank',  # Assuming it's from a bank account
            'amount': -total_amount_due,  # Negative because it's a debit
        })

        # Classify each expense item using Azure LLM
        for expense_name, expense_amount in expenses:
            account = get_account_for_item(expense_name.strip())
            extracted_transactions.append({
                'transaction_date': '2024-10-31',  # Placeholder for transaction date
                'description': expense_name.strip(),
                'account': account,
                'amount': float(expense_amount),  # Positive because it's a credit
            })

    return extracted_transactions

def get_account_for_expense(expense_name):
    """
    Maps expense names to account names based on your chart of accounts.
    """
    # Add your mapping logic here based on the ACCOUNT_CLASSIFICATIONS
    # Example:
    if expense_name == 'HOA Fees':
        return 'Home Owners Association Fees'
    elif expense_name == 'Maintenance':
        return 'Maintenance and Repairs'
    # ... add more mappings ...
    else:
        return 'Other Expenses'  # Default account for unmatched expenses

def get_account_for_item(item_name):
    """
    Maps item names (expenses, liabilities, assets, revenue, equity) 
    to account names based on your chart of accounts using Azure LLM.
    """
    # Clean and preprocess the item name (if needed)
    processed_name = item_name.strip().lower()

    # Use Azure LLM for classification
    account = classify_transaction_with_azure(item_name)

    # If classification fails or doesn't match an account, fallback to a default
    if account == "Uncategorized":
        current_app.logger.warning(f"Unable to classify the item '{item_name}', using default classification.")
        return "Uncategorized"  # Default account or error handling logic

    return account