import joblib
import PyPDF2
import re
from collections import defaultdict
from datetime import datetime
import os

def load_model():
    try:
        # Adjust this path to where your model file is stored
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'expense_classifier.joblib')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
            
        model = joblib.load(model_path)
        return model
        
    except Exception as e:
        raise Exception(f"Failed to load model: {str(e)}")

def classify_expense(description, model=None):
    """Classify an expense description"""
    if model is None:
        model = load_model()
    
    # Predict category
    category = model.predict([description])[0]
    
    # Get probability scores
    probabilities = model.predict_proba([description])[0]
    confidence = max(probabilities)
    
    return {
        'category': category,
        'confidence': confidence
    }

def extract_text_from_pdf(filepath):
    """Extract text from PDF file"""
    try:
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text() + '\n'
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return None

def is_expense_line(line):
    """
    Check if a line contains expense information
    Returns True if line contains both amount and description
    """
    # Amount patterns for different currencies
    amount_pattern = r'(?:USD|R|ZAR|£|\$)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)'
    
    # Common expense keywords
    expense_keywords = [
        'fee', 'charge', 'payment', 'expense', 'cost', 'bill',
        'maintenance', 'repair', 'service', 'tax', 'insurance',
        'utility', 'water', 'electricity', 'gas', 'assessment'
    ]
    
    try:
        # Check if line contains an amount
        has_amount = bool(re.search(amount_pattern, line))
        
        # Check if line contains any expense keywords
        has_keyword = any(keyword in line.lower() for keyword in expense_keywords)
        
        # Line should have both amount and keyword
        return has_amount and has_keyword
        
    except Exception as e:
        print(f"Error checking expense line: {str(e)}")
        return False

def extract_amount(line):
    """Extract amount from expense line"""
    # Amount pattern with currency symbols
    amount_pattern = r'(?:USD|R|ZAR|£|\$)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)'
    
    try:
        match = re.search(amount_pattern, line)
        if match:
            # Clean amount string
            amount_str = match.group(1)
            
            # Remove currency symbols and spaces
            amount_str = re.sub(r'[^\d.,]', '', amount_str)
            
            # Handle different decimal separators
            if ',' in amount_str and '.' in amount_str:
                # If both exist, assume comma is thousand separator
                amount_str = amount_str.replace(',', '')
            elif ',' in amount_str:
                # If only comma exists, assume it's decimal separator
                amount_str = amount_str.replace(',', '.')
            
            return float(amount_str)
        return 0.0
        
    except Exception as e:
        print(f"Error extracting amount: {str(e)}")
        return 0.0

def extract_description(line):
    """Extract description from expense line"""
    # Amount pattern with currency symbols
    amount_pattern = r'(?:USD|R|ZAR|£|\$)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)'
    
    try:
        # Remove amount from line
        description = re.sub(amount_pattern, '', line)
        
        # Clean up the description
        description = description.strip()
        description = re.sub(r'\s+', ' ', description)  # Remove extra whitespace
        description = re.sub(r'[^\w\s-]', '', description)  # Remove special characters
        
        return description
        
    except Exception as e:
        print(f"Error extracting description: {str(e)}")
        return ''

def organize_expenses(expenses):
    """
    Organize extracted expenses by category
    Returns structured data with totals and details
    """
    try:
        # Initialize result structure
        result = {
            'success': True,
            'totals': defaultdict(float),
            'details': defaultdict(list),
            'metadata': {
                'processed_at': datetime.now().isoformat(),
                'total_items': len(expenses),
                'categories_found': set()
            }
        }
        
        # Process each expense
        for expense in expenses:
            category = expense['category']
            amount = expense['amount']
            
            # Add to totals
            result['totals'][category] += amount
            
            # Add to details
            result['details'][category].append({
                'description': expense['description'],
                'amount': amount,
                'confidence': expense['confidence']
            })
            
            # Track categories found
            result['metadata']['categories_found'].add(category)
        
        # Convert sets to lists for JSON serialization
        result['metadata']['categories_found'] = list(result['metadata']['categories_found'])
        
        # Convert defaultdict to regular dict
        result['totals'] = dict(result['totals'])
        result['details'] = dict(result['details'])
        
        return result
        
    except Exception as e:
        print(f"Error organizing expenses: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

# Example usage in extract_expenses_from_pdf:
def extract_expenses_from_pdf(filepath):
    """Extract and classify expenses from PDF"""
    try:
        # Extract text from PDF
        text = extract_text_from_pdf(filepath)
        if not text:
            return None
        
        # Load the model
        model = load_model()
        
        # Process each line
        expenses = []
        for line in text.split('\n'):
            if is_expense_line(line):
                amount = extract_amount(line)
                description = extract_description(line)
                
                if amount > 0 and description:
                    # Classify the expense
                    classification = classify_expense(description, model)
                    
                    expenses.append({
                        'description': description,
                        'amount': amount,
                        'category': classification['category'],
                        'confidence': classification['confidence']
                    })
        
        # Organize and return results
        return organize_expenses(expenses)
        
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None 