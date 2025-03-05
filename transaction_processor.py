from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
from flask import current_app
import spacy
import pdfplumber
import pandas as pd
from app_constants import (
    ACCOUNTS, MAIN_CATEGORIES, SUBCATEGORIES, 
    ACCOUNT_CLASSIFICATIONS, EXPENSE_CLASSIFICATIONS
)
from utils.document_processor import DocumentProcessor

class TransactionProcessor:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        
    def process_document(self, filepath: str) -> List[Dict[str, Any]]:
        """Process document and extract transactions using DocumentProcessor."""
        try:
            # Use DocumentProcessor to extract raw transaction data
            raw_transactions = self.doc_processor.process_document(filepath)
            
            # Process and enrich each transaction
            processed_transactions = []
            for raw_transaction in raw_transactions:
                processed_transaction = self._enrich_transaction(raw_transaction)
                if processed_transaction:
                    processed_transactions.append(processed_transaction)
                    
            return processed_transactions
            
        except Exception as e:
            current_app.logger.error(f"Error processing document: {str(e)}")
            return []

    def _enrich_transaction(self, raw_transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich raw transaction with additional classification and validation."""
        try:
            # Get the description and amount for classification
            description = raw_transaction.get('description', '')
            amount = raw_transaction.get('debit_amount') or raw_transaction.get('credit_amount', Decimal('0.00'))
            
            # Use DocumentProcessor's NLP capabilities for classification
            classification = self.doc_processor._classify_text(description)
            
            # Generate standardized description
            standardized_description = self.doc_processor._generate_description(
                description, 
                classification
            )
            
            # Calculate confidence score
            confidence_score = self.doc_processor._calculate_confidence(description)
            
            # Create enriched transaction
            enriched_transaction = {
                'transaction_date': raw_transaction.get('transaction_date', datetime.utcnow()),
                'processed_date': datetime.utcnow(),
                'last_modified': datetime.utcnow(),
                'debit_amount': raw_transaction.get('debit_amount', Decimal('0.00')),
                'credit_amount': raw_transaction.get('credit_amount', Decimal('0.00')),
                'main_category': classification.get('main_category', 'Uncategorized'),
                'sub_category': classification.get('sub_category', 'Uncategorized'),
                'account': classification.get('specific_account', 'Uncategorized'),
                'description': standardized_description,
                'reference_number': raw_transaction.get('reference_number'),
                'document': raw_transaction.get('document'),
                'document_type': raw_transaction.get('document_type'),
                'extracted_data': {
                    'raw_text': description,
                    'classification_data': classification,
                    'original_data': raw_transaction.get('extracted_data', {})
                },
                'confidence_score': confidence_score,
                'is_verified': False,
                'is_reconciled': False,
                'is_portfolio': False
            }
            
            return enriched_transaction
            
        except Exception as e:
            current_app.logger.error(f"Error enriching transaction: {str(e)}")
            return None

    def validate_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Validate transaction data."""
        required_fields = [
            'transaction_date',
            'main_category',
            'sub_category',
            'account'
        ]
        
        # Check required fields
        if not all(transaction.get(field) for field in required_fields):
            return False
            
        # Validate amounts
        debit = transaction.get('debit_amount', Decimal('0.00'))
        credit = transaction.get('credit_amount', Decimal('0.00'))
        
        if not isinstance(debit, Decimal) or not isinstance(credit, Decimal):
            return False
            
        if debit < 0 or credit < 0:
            return False
            
        # Validate categories
        if transaction['main_category'] not in MAIN_CATEGORIES:
            return False
            
        if transaction['main_category'] in SUBCATEGORIES:
            if transaction['sub_category'] not in SUBCATEGORIES[transaction['main_category']]:
                return False
                
        return True 