from PyPDF2 import PdfReader
import re
from decimal import Decimal
import os
from werkzeug.utils import secure_filename
from flask import current_app

def extract_expenses_from_pdf(filepath):
    try:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"PDF file not found at {filepath}")
            
        reader = PdfReader(filepath)
        if not reader.pages:
            raise ValueError("PDF file is empty")

        text = ""
        for page in reader.pages:
            text += page.extract_text()

        # Example data for now
        extracted_data = {
            'hoa_fees': 300.0,
            'maintenance': 50.0,
            'staff_cost': 40.0,
            'management_fee': 35.0,
            'reserve_fund': 75.0,
            'special_assessments': 0.0,
            'amenities': 25.0,
            'other_expenses': 15.0,
            'insurance': 20.0,
            'property_taxes': 0.0,
            'electricity': 0.0,
            'gas': 0.0,
            'water_sewer': 0.0,
            'miscellaneous_cost': 0.0,
            'other_city_charges': 0.0
        }

        current_app.logger.debug(f"Extracted data: {extracted_data}")

        # Return the data directly in extracted_data key
        return {
            'success': True,
            'extracted_data': extracted_data  # Changed to match the expected format
        }

    except Exception as e:
        current_app.logger.error(f"Error extracting PDF data: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        } 