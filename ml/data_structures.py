EXPENSE_CATEGORIES = [
    'hoa_fees',
    'maintenance',
    'staff_cost',
    'management_fee',
    'reserve_fund',
    'special_assessments',
    'amenities',
    'other_expenses',
    'insurance',
    'property_taxes',
    'electricity',
    'gas',
    'water_sewer',
    'miscellaneous_cost',
    'other_city_charges'
]

# Example training data format
TRAINING_DATA = [
    {
        'text': 'Monthly HOA Fee Payment',
        'category': 'hoa_fees'
    },
    {
        'text': 'Electricity Bill Payment',
        'category': 'electricity'
    },
    # Add more examples...
] 