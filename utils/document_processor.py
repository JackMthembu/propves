from flask import current_app
import pdfplumber
import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
import re
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from app_constants import ACCOUNT_CLASSIFICATIONS, EXPENSE_CLASSIFICATIONS
import csv
import os

class DocumentProcessor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_md")
        # Initialize classification vectors
        self.category_vectors = self._initialize_category_vectors()
        self.amount_pattern = re.compile(r'\$?\d+(?:,\d{3})*(?:\.\d{2})?')
        self.date_pattern = re.compile(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}')
        
    def _initialize_category_vectors(self):
        """Initialize NLP vectors for all categories and accounts"""
        vectors = {
            'main_categories': {},
            'sub_categories': {},
            'accounts': {},
            'keywords': {}
        }
        
        # Process ACCOUNT_CLASSIFICATIONS
        for main_cat, accounts in ACCOUNT_CLASSIFICATIONS.items():
            # Process main category
            vectors['main_categories'][main_cat] = self.nlp(main_cat.lower())
            
            # Since accounts is a list, not a dict, handle differently
            for account in accounts:
                account_key = f"{main_cat}:{account}"
                vectors['accounts'][account_key] = self.nlp(account.lower())
        
        # Process EXPENSE_CLASSIFICATIONS
        for main_cat, sub_cats in EXPENSE_CLASSIFICATIONS.items():
            # Add main category if not already added
            if main_cat not in vectors['main_categories']:
                vectors['main_categories'][main_cat] = self.nlp(main_cat.lower())
            
            # Process subcategories and their items
            for sub_cat, items in sub_cats.items():
                sub_cat_key = f"{main_cat}:{sub_cat}"
                vectors['sub_categories'][sub_cat_key] = self.nlp(sub_cat.lower())
                
                # Process items as keywords
                if main_cat not in vectors['keywords']:
                    vectors['keywords'][main_cat] = []
                vectors['keywords'][main_cat].extend([self.nlp(item.lower()) for item in items])

        return vectors

    def _classify_text(self, text, threshold=0.60):
        """Classify text using NLP similarity scores"""
        text_doc = self.nlp(text.lower())
        classification = {
            'main_category': None,
            'sub_category': None,
            'specific_account': None,
            'confidence': 0.0,
            'keyword_matches': []
        }

        # Check keyword matches first
        keyword_matches = []
        for category, keyword_vectors in self.category_vectors['keywords'].items():
            for keyword_vec in keyword_vectors:
                similarity = text_doc.similarity(keyword_vec)
                if similarity > threshold:
                    keyword_matches.append((category, similarity))

        # Find best matching main category
        best_main_score = 0
        for main_cat, main_vec in self.category_vectors['main_categories'].items():
            similarity = text_doc.similarity(main_vec)
            if similarity > best_main_score:
                best_main_score = similarity
                classification['main_category'] = main_cat

        if classification['main_category']:
            # Find best matching subcategory within the main category
            best_sub_score = 0
            for sub_key, sub_vec in self.category_vectors['sub_categories'].items():
                if sub_key.startswith(classification['main_category']):
                    similarity = text_doc.similarity(sub_vec)
                    if similarity > best_sub_score:
                        best_sub_score = similarity
                        classification['sub_category'] = sub_key.split(':')[1]

            # Find best matching account within the subcategory
            best_account_score = 0
            for account_key, account_vec in self.category_vectors['accounts'].items():
                if account_key.startswith(f"{classification['main_category']}:{classification['sub_category']}"):
                    similarity = text_doc.similarity(account_vec)
                    if similarity > best_account_score:
                        best_account_score = similarity
                        classification['specific_account'] = account_key.split(':')[2]

            # Calculate overall confidence score
            classification['confidence'] = (best_main_score + best_sub_score + best_account_score) / 3
            classification['keyword_matches'] = keyword_matches

        return classification

    def _enhance_classification(self, text, initial_classification):
        """Enhance classification using additional context and rules"""
        doc = self.nlp(text.lower())
        
        # Extract monetary values and dates
        amounts = [ent.text for ent in doc.ents if ent.label_ == 'MONEY']
        dates = [ent.text for ent in doc.ents if ent.label_ == 'DATE']
        orgs = [ent.text for ent in doc.ents if ent.label_ == 'ORG']

        # Apply business rules based on context
        if initial_classification['main_category'] == 'Operating Expenses':
            if any(org in text.lower() for org in ['utility', 'power', 'gas', 'water']):
                initial_classification['sub_category'] = 'Utilities'
            elif any(word in text.lower() for word in ['repair', 'fix', 'maintain']):
                initial_classification['sub_category'] = 'Maintenance & Repairs'

        # Adjust confidence based on additional context
        context_score = 0
        if amounts: context_score += 0.2
        if dates: context_score += 0.2
        if orgs: context_score += 0.2

        initial_classification['confidence'] = min(
            1.0, 
            initial_classification['confidence'] + context_score
        )

        return initial_classification

    def classify_transaction(self, text):
        """Main classification method combining NLP and rule-based approaches"""
        # Get keyword matches
        keyword_matches = self._get_keyword_matches(text)
        
        # Extract patterns
        patterns = self._extract_patterns(text)
        
        # Initial classification from strongest keyword matches
        classification = {
            'main_category': None,
            'sub_category': None,
            'specific_account': None,
            'confidence': 0.0,
            'transaction_type': None,
            'patterns': patterns,
            'keyword_matches': keyword_matches
        }
        
        # Determine transaction type and category based on keyword matches
        if keyword_matches:
            top_category, top_score, _ = keyword_matches[0]
            
            # Map keyword category to transaction classification
            classification.update(
                self._map_keyword_to_classification(top_category, top_score)
            )
        
        return classification

    def process_document(self, filepath):
        """Process document and extract transactions"""
        try:
            transactions = []
            
            # Handle PDF files
            if filepath.lower().endswith('.pdf'):
                with pdfplumber.open(filepath) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            # Split text into lines and process each line
                            lines = text.split('\n')
                            for line in lines:
                                if line.strip():  # Skip empty lines
                                    transaction = self._extract_transaction_data(line)
                                    if transaction:
                                        transactions.append(transaction)
            
            # Handle CSV files
            elif filepath.lower().endswith('.csv'):
                df = pd.read_csv(filepath)
                transactions.extend(self._process_dataframe(df))
            
            # Handle Excel files
            elif filepath.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
                transactions.extend(self._process_dataframe(df))
            
            current_app.logger.debug(f"Extracted {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            current_app.logger.error(f"Error processing document: {str(e)}")
            current_app.logger.exception("Full traceback:")
            return []  # Return empty list instead of raising exception

    def _process_dataframe(self, df):
        """Process a pandas DataFrame and extract transactions"""
        transactions = []
        try:
            date_col = self._find_date_column(df)
            amount_col = self._find_amount_column(df)
            desc_col = self._find_description_column(df)
            
            if all([date_col, amount_col, desc_col]):
                for _, row in df.iterrows():
                    transaction = {
                        'transaction_date': self._parse_date(row[date_col]) or datetime.now(),
                        'description': str(row[desc_col]),
                        'debit_amount': Decimal('0'),
                        'credit_amount': Decimal('0'),
                        'account': 'Uncategorized',
                        'main_category': None,
                        'sub_category': None,
                        'confidence_score': 0.0
                    }
                    
                    # Parse amount
                    amount = self._parse_amount(str(row[amount_col]))
                    if amount:
                        if amount > 0:
                            transaction['debit_amount'] = amount
                        else:
                            transaction['credit_amount'] = abs(amount)
                    
                    # Classify transaction
                    classification = self._classify_text(str(row[desc_col]))
                    if classification['main_category']:
                        transaction.update({
                            'main_category': classification['main_category'],
                            'sub_category': classification['sub_category'],
                            'account': classification['specific_account'] or 'Uncategorized',
                            'confidence_score': classification['confidence']
                        })
                    
                    transactions.append(transaction)
        except Exception as e:
            current_app.logger.error(f"Error processing DataFrame: {str(e)}")
        
        return transactions

    def _extract_transaction_data(self, text):
        """Extract transaction data from a line of text"""
        try:
            # Initialize default transaction dictionary
            transaction = {
                'transaction_date': datetime.now(),
                'description': text.strip(),
                'debit_amount': Decimal('0'),
                'credit_amount': Decimal('0'),
                'account': 'Uncategorized',
                'main_category': None,
                'sub_category': None,
                'confidence_score': 0.0
            }

            # Extract date
            date_match = self.date_pattern.search(text)
            if date_match:
                try:
                    transaction['transaction_date'] = pd.to_datetime(date_match.group()).to_pydatetime()
                except:
                    pass  # Keep default date if parsing fails

            # Extract amount
            amount_match = self.amount_pattern.search(text)
            if amount_match:
                try:
                    amount = Decimal(amount_match.group().replace('$', '').replace(',', ''))
                    if amount > 0:
                        transaction['debit_amount'] = amount
                    else:
                        transaction['credit_amount'] = abs(amount)
                except:
                    pass  # Keep default amounts if parsing fails

            # Classify the transaction
            classification = self._classify_text(text)
            if classification['main_category']:
                transaction.update({
                    'main_category': classification['main_category'],
                    'sub_category': classification['sub_category'],
                    'account': classification['specific_account'] or 'Uncategorized',
                    'confidence_score': classification['confidence']
                })

            # Calculate confidence score
            if not transaction['confidence_score']:
                transaction['confidence_score'] = self._calculate_confidence(text)

            return transaction

        except Exception as e:
            current_app.logger.error(f"Error extracting transaction data: {str(e)}")
            # Return a basic transaction rather than None
            return {
                'transaction_date': datetime.now(),
                'description': text.strip(),
                'debit_amount': Decimal('0'),
                'credit_amount': Decimal('0'),
                'account': 'Uncategorized',
                'main_category': None,
                'sub_category': None,
                'confidence_score': 0.0
            }

    def _process_csv(self, filepath):
        """Process a CSV file and return a list of transaction dictionaries."""
        transactions = []
        try:
            with open(filepath, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    transaction = {
                        'date': row.get('date'),
                        'description': row.get('description'),
                        'amount': float(row.get('amount', 0)),
                        'type': row.get('type'),
                        # Add other fields as needed
                    }
                    transactions.append(transaction)
            return transactions
        except Exception as e:
            current_app.logger.error(f"CSV processing error: {str(e)}")
            raise

    def _process_pdf(self, filepath):
        """Process a PDF file and return a list of transaction dictionaries."""
        transactions = []
        try:
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            if line.strip():
                                date_match = self.date_pattern.search(line)
                                amount_match = self.amount_pattern.search(line)
                                
                                # Only process lines with at least a date or amount
                                if date_match or amount_match:
                                    # Initialize transaction with required fields from model
                                    transaction = {
                                        # Required fields (nullable=False)
                                        'transaction_date': datetime.utcnow(),
                                        'processed_date': datetime.utcnow(),
                                        'last_modified': datetime.utcnow(),
                                        'main_category': 'Uncategorized',
                                        'sub_category': 'Uncategorized',
                                        'account': 'Uncategorized',
                                        
                                        # Optional fields (nullable=True)
                                        'debit_amount': None,
                                        'credit_amount': None,
                                        'description': line.strip()[:200],  # Respect max length
                                        'reference_number': None,
                                        'document': os.path.basename(filepath)[:255],  # Respect max length
                                        'document_type': 'pdf'[:10],  # Respect max length
                                        'extracted_data': {
                                            'raw_text': line.strip(),
                                            'extraction_method': 'pdf_text'
                                        },
                                        'confidence_score': 0.0,
                                        'property_id': None,  # These would be set later
                                        'owner_id': None,     # based on context
                                        
                                        # Boolean flags
                                        'is_verified': False,
                                        'is_reconciled': False,
                                        'is_portfolio': False
                                    }
                                    
                                    # Parse date if found (required field)
                                    if date_match:
                                        try:
                                            parsed_date = pd.to_datetime(date_match.group())
                                            transaction['transaction_date'] = parsed_date.to_pydatetime()
                                        except Exception as e:
                                            current_app.logger.debug(f"Date parsing error: {str(e)}")
                                            continue  # Skip this transaction if date parsing fails
                                    
                                    # Parse amount if found
                                    if amount_match:
                                        try:
                                            amount = Decimal(amount_match.group().replace('$', '').replace(',', ''))
                                            # Ensure amounts have 2 decimal places
                                            if amount > 0:
                                                transaction['debit_amount'] = Decimal(str(amount)).quantize(Decimal('0.01'))
                                                transaction['credit_amount'] = Decimal('0.00')
                                            else:
                                                transaction['debit_amount'] = Decimal('0.00')
                                                transaction['credit_amount'] = abs(amount).quantize(Decimal('0.01'))
                                        except Exception as e:
                                            current_app.logger.debug(f"Amount parsing error: {str(e)}")
                                    
                                    # Classify the transaction (required fields)
                                    classification = self._classify_text(line)
                                    if classification.get('main_category'):
                                        transaction.update({
                                            'main_category': classification['main_category'][:50],  # Respect max length
                                            'sub_category': (classification.get('sub_category') or 'Uncategorized')[:50],
                                            'account': (classification.get('specific_account') or 'Uncategorized')[:50],
                                            'confidence_score': float(classification.get('confidence', 0.0))
                                        })
                                    
                                    # Only add transactions with required fields
                                    if all(transaction.get(field) is not None 
                                          for field in ['transaction_date', 'main_category', 'sub_category', 'account']):
                                        transactions.append(transaction)
                                    
            current_app.logger.debug(f"Extracted {len(transactions)} transactions from PDF")
            return transactions
            
        except Exception as e:
            current_app.logger.error(f"PDF processing error: {str(e)}")
            current_app.logger.exception("Full traceback:")
            return []

    def _extract_transaction_from_text(self, text):
        """Enhanced extraction with double-entry support"""
        date_match = self.date_pattern.search(text)
        amount_match = self.amount_pattern.search(text)
        
        if not (date_match and amount_match):
            return None
            
        amount = self._parse_amount(amount_match.group())
        entry_data = self._classify_transaction_entry(text, amount)
        
        return {
            'transaction_date': self._parse_date(date_match.group()),
            'debit_amount': entry_data['debit_amount'],
            'credit_amount': entry_data['credit_amount'],
            'main_category': entry_data['classification']['main_category'],
            'sub_category': entry_data['classification']['subcategory'],
            'account': entry_data['classification']['specific_account'],
            'description': self._generate_description(text, entry_data['classification']),
            'confidence_score': entry_data['classification']['confidence']
        }

    def _classify_transaction_entry(self, text, amount):
        """Determine if amount should be debit or credit based on transaction type"""
        classification = self._classify_transaction(text)
        main_category = classification['main_category']
        
        # Determine debit/credit based on accounting rules
        debit_amount = None
        credit_amount = None
        
        if main_category == "Assets":
            if amount > 0:  # Increase in assets
                debit_amount = amount
            else:  # Decrease in assets
                credit_amount = abs(amount)
                
        elif main_category == "Liabilities":
            if amount > 0:  # Increase in liabilities
                credit_amount = amount
            else:  # Decrease in liabilities
                debit_amount = abs(amount)
                
        elif main_category == "Income":
            credit_amount = abs(amount)  # Income is always credited
            
        elif main_category in ["Operating Expenses", "Occupancy Expenses", 
                             "Common Area Expenses", "Financial Expenses", 
                             "Non-Operating Items"]:
            debit_amount = abs(amount)  # Expenses are always debited
            
        return {
            'debit_amount': debit_amount,
            'credit_amount': credit_amount,
            'classification': classification
        }

    def _generate_description(self, text, classification):
        """Generate standardized transaction description"""
        doc = self.nlp(text)
        
        # Extract entities
        entities = {ent.label_: ent.text for ent in doc.ents}
        
        # Build description components
        components = []
        
        # Add transaction type
        if classification['main_category'] in ['Assets', 'Liabilities']:
            components.append(f"{classification['main_category']} - {classification['subcategory']}")
        
        # Add specific account
        components.append(classification['specific_account'])
        
        # Add organization if found
        if 'ORG' in entities:
            components.append(f"with {entities['ORG']}")
        
        # Add date context if found
        if 'DATE' in entities and not self.date_pattern.search(entities['DATE']):
            components.append(f"for {entities['DATE']}")
        
        # Add any monetary context
        if 'MONEY' in entities and not self.amount_pattern.search(entities['MONEY']):
            components.append(f"ref: {entities['MONEY']}")
        
        return " - ".join(filter(None, components))

    def _classify_transaction(self, description):
        """Classify transaction based on description"""
        categories = list(ACCOUNT_CLASSIFICATIONS.keys())
        result = self.nlp(description, categories)
        return result['labels'][0]

    def _calculate_confidence(self, text):
        """Calculate confidence score for extraction"""
        # Implement confidence scoring based on your criteria
        score = 0.0
        if self.date_pattern.search(text): score += 0.3
        if self.amount_pattern.search(text): score += 0.3
        if len(text.split()) > 3: score += 0.4
        return score

    @staticmethod
    def _find_date_column(df):
        """Identify date column in DataFrame"""
        date_keywords = ['date', 'transaction_date', 'trans_date']
        return next((col for col in df.columns if any(k in col.lower() for k in date_keywords)), None)

    @staticmethod
    def _find_amount_column(df):
        """Identify amount column in DataFrame"""
        amount_keywords = ['amount', 'sum', 'total', 'price']
        return next((col for col in df.columns if any(k in col.lower() for k in amount_keywords)), None)

    @staticmethod
    def _find_description_column(df):
        """Identify description column in DataFrame"""
        desc_keywords = ['description', 'desc', 'details', 'narrative']
        return next((col for col in df.columns if any(k in col.lower() for k in desc_keywords)), None)

    @staticmethod
    def _parse_date(date_str):
        """Parse date string to datetime object"""
        try:
            return pd.to_datetime(date_str).to_pydatetime()
        except:
            return None

    @staticmethod
    def _parse_amount(amount_str):
        """Parse amount string to Decimal"""
        try:
            # Remove currency symbols and convert to Decimal
            amount = str(amount_str).replace('$', '').replace(',', '')
            return Decimal(amount)
        except:
            return None 

class TransactionProcessor:
    def __init__(self):
        self.transactions = []

    def process_file(self, filepath):
        """Process the uploaded transaction file"""
        try:
            self.transactions = DocumentProcessor().process_document(filepath)
            return True
        except Exception as e:
            raise Exception(f"Error processing file: {str(e)}")
        
    def get_transactions(self):
        """Return processed transactions"""
        return self.transactions 