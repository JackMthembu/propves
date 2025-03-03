# utils.py
import os
import secrets
from PIL import Image
from flask import current_app

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'csv', 'xls', 'xlsx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_photo(photo):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(photo.filename)
    photo_filename = random_hex + f_ext
    photo_path = os.path.join(current_app.root_path, 'static/uploads/property_photos', 
 photo_filename)

    output_size = (800, 600)
    i = Image.open(photo)
    i.thumbnail(output_size)
    i.save(photo_path)

    return photo_filename

def get_expense_fields():
    """Return a dictionary of expense field names and their display labels"""
    return {
        'hoa_fees': 'Association Fees',
        'maintenance': 'Maintenance',
        'staff_cost': 'Staff Cost',
        'management_fee': 'Management Fee',
        'reserve_fund': 'Reserve Fund',
        'special_assessments': 'Special Assessments',
        'amenities': 'Amenities',
        'other_expenses': 'Other Expenses',
        'insurance': 'Insurance',
        'property_taxes': 'Property Taxes',
        'electricity': 'Electricity',
        'gas': 'Gas',
        'water_sewer': 'Water & Sewer',
        'miscellaneous_cost': 'Miscellaneous',
        'other_city_charges': 'Other City Charges'
    }

def format_currency(value):
    return "${:,.2f}".format(value)
