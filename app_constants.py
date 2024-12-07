MAIN_CATEGORIES = {
    "Assets": ["Current Asset", "Non-Current Asset"],
    "Liabilities": ["Current Liability", "Non-Current Liability"],
    "Equity": ["Equity"],
    "Revenue": ["Income"],
    "Expenses": [
        "Administrative Expenses",
        "Utilities",
        "Common Area Expenses",
        "Financial Expenses",
        "Marketing Expenses",
        "Property Management Expenses",
    ],
}

SUB_CATEGORIES = {
    "Current Asset": [
        "Accounts Receivable",
        "Prepaid Rent",
        "Prepaid Insurance",
    ],
    "Non-Current Asset": [
        "Property Plant and Equipment",
        "Leasehold Improvements",
    ],
    "Current Liability": [
        "Accounts Payable",
        "Unearned Rent",
        "Deferred Revenue",
    ],
    "Non-Current Liability": [
        "Mortgage Payable",
        "Long-Term Debt",
    ],
    "Equity": [
        "Contributed Capital",
        "Retained Earnings (Current Year)",
        "Retained Earnings (Accumulated)",
        "Owner's Withdrawals",
    ],
    "Income": [
        "Rental Income",
        "Other Revenue",
        "Parking Fees",
        "Pet Fees",
    ],
    "Administrative Expenses": [
        "Property Management Fees",
        "Property Insurance",
        "Pest Control",
        "Signage",
    ],
    "Utilities": [
        "Lighting",
        "Waste Management",
        "HVAC Maintenance",
    ],
    "Common Area Expenses": [
        "Common Area Utilities",
        "Landscaping",
        "Snow Removal",
    ],
    "Financial Expenses": [
        "Bank Fees",
        "Credit Card Processing Fees",
        "Loan Processing Fees",
    ],
    "Marketing Expenses": [
        "Marketing and Advertising",
    ],
    "Property Management Expenses": [
        "Elevator Maintenance",
        "Lobby Maintenance",
        "Parking Lot Maintenance",
    ],
}

ACCOUNTS = {
    "Accounts Receivable": ("Assets", "Current Asset"),
    "Prepaid Rent": ("Assets", "Current Asset"),
    "Prepaid Insurance": ("Assets", "Current Asset"),
    "Property Plant and Equipment": ("Assets", "Non-Current Asset"),
    "Leasehold Improvements": ("Assets", "Non-Current Asset"),
    "Accounts Payable": ("Liabilities", "Current Liability"),
    "Unearned Rent": ("Liabilities", "Current Liability"),
    "Deferred Revenue": ("Liabilities", "Current Liability"),
    "Mortgage Payable": ("Liabilities", "Non-Current Liability"),
    "Long-Term Debt": ("Liabilities", "Non-Current Liability"),
    "Contributed Capital": ("Equity", "Equity"),
    "Retained Earnings (Current Year)": ("Equity", "Equity"),
    "Retained Earnings (Accumulated)": ("Equity", "Equity"),
    "Owner's Withdrawals": ("Equity", "Equity"),
    "Rental Income": ("Revenue", "Income"),
    "Other Revenue": ("Revenue", "Income"),
    "Parking Fees": ("Revenue", "Income"),
    "Pet Fees": ("Revenue", "Income"),
    "Property Management Fees": ("Expenses", "Administrative Expenses"),
    "Property Insurance": ("Expenses", "Administrative Expenses"),
    "Pest Control": ("Expenses", "Administrative Expenses"),
    "Signage": ("Expenses", "Administrative Expenses"),
    "Lighting": ("Expenses", "Utilities"),
    "Waste Management": ("Expenses", "Utilities"),
    "HVAC Maintenance": ("Expenses", "Utilities"),
    "Common Area Utilities": ("Expenses", "Common Area Expenses"),
    "Landscaping": ("Expenses", "Common Area Expenses"),
    "Snow Removal": ("Expenses", "Common Area Expenses"),
    "Bank Fees": ("Expenses", "Financial Expenses"),
    "Credit Card Processing Fees": ("Expenses", "Financial Expenses"),
    "Loan Processing Fees": ("Expenses", "Financial Expenses"),
    "Marketing and Advertising": ("Expenses", "Marketing Expenses"),
    "Elevator Maintenance": ("Expenses", "Property Management Expenses"),
    "Lobby Maintenance": ("Expenses", "Property Management Expenses"),
    "Parking Lot Maintenance": ("Expenses", "Property Management Expenses"),
}


# Flat list of all accounts (if needed)
ALL_ACCOUNTS = [
    account
    for category in ACCOUNTS.values()
    for account in category
]


# Special case for dual classification
DUAL_CLASSIFICATION_ITEMS = {
    "Tenant Improvements": {
        "Asset": ["Assets", "Non-Current Assets (Leasehold Improvements)"],
        "Expense": ["Expenses", "Operating Expenses (Maintenance)"]
    }
}

# Add EXPENSE_CLASSIFICATIONS based on the existing structure
EXPENSE_CLASSIFICATIONS = {
    "Operating Expenses": {
        "Administrative": [
            "Administrative Expenses"
        ],
        "Insurance": [
            "Insurance",
            "Property Insurance"
        ],
        "Professional Fees": [
            "Legal and Professional Fees"
        ],
        "Repairs and Maintenance": [
            "Maintenance and Repairs",
            "Pest Control"
        ],
        "Advertising": [
            "Marketing and Advertising",
            "Signage"
        ],
        "Management Fees": [
            "Property Management Fees"
        ],
        "Property Taxes": [
            "Property Taxes",
            "Property Tax Assessments"
        ],
        "Security": [
            "Security Services",
            "Security Systems"
        ],
        "Utilities": [
            "Utilities",
            "Common Area Utilities",
            "Lighting",
            "Waste Management"
        ],
        "Cleaning and Maintenance": [
            "Cleaning Services",
            "Common Area Maintenance (CAM)",
            "Elevator Maintenance",
            "HVAC Maintenance",
            "Landscaping",
            "Lobby Maintenance",
            "Parking Lot Maintenance",
            "Snow Removal"
        ],
        "Rent": [
            "Lease Payments",
            "Rent"
        ]
    },
    "Financial Expenses": {
        "Bank and Processing Fees": [
            "Bank Fees",
            "Credit Card Processing Fees",
            "Late Payment Penalties",
            "Loan Processing Fees"
        ],
        "Interest": [
            "Mortgage Interest"
        ]
    }
}

ACCOUNT_CLASSIFICATIONS = {
    'Assets': [
        'Accounts Receivable',
        'Building',
        'Equipment',
        'Furniture and Fixtures',
        'Land',
        'Leasehold Improvements',
        'Prepaid Expenses',
        'Prepaid Insurance',
        'Prepaid Rent',
        'Property, Plant, and Equipment'
    ],
    'Liabilities': [
        'Accounts Payable',
        'Accrued Expenses',
        'Deferred Revenue',
        'Long-Term Debt',
        'Maintenance Reserves',
        'Mortgage Payable',
        'Prepaid Rent',
        'Property Tax Payable',
        'Security Deposits',
        'Unearned Rent'
    ],
    'Equity': [
        'Contributed Capital',
        'Current Year Earnings',
        'Distributions',
        'Owner\'s Capital',
        'Owner\'s Withdrawals',
        'Partner Contributions',
        'Retained Earnings',
        'Retained Earnings (Accumulated)',
        'Retained Earnings (Current Year)'
    ],
    'Revenue': [
        'Application Fees',
        'Common Area Revenue',
        'Late Fee Income',
        'Other Revenue',
        'Parking Fees',
        'Pet Rent',
        'Rental Income',
        'Storage Unit Rental',
        'Utility Reimbursements'
    ],
    'Expenses': [
            'Administrative Expenses',
            'Insurance',
            'Legal and Professional Fees',
            'Maintenance and Repairs',
            'Marketing and Advertising',
            'Pest Control',
            'Property Management Fees',
            'Property Taxes',
            'Security Services',
            'Utilities',
            'Common Area Maintenance (CAM)',
            'Common Area Utilities',
            'Landscaping',
            'Lighting',
            'Lobby Maintenance',
            'Parking Lot Maintenance',
            'Security Systems',
            'Signage',
            'Snow Removal',
            'Cleaning Services',
            'Elevator Maintenance',
            'Maintenance and Repairs',
            'Lease Payments',
            'Rent',
            'Tenant Improvements',
            'Waste Management',
            'Bank Fees',
            'Credit Card Processing Fees',
            'Late Payment Penalties',
            'Loan Processing Fees',
            'Mortgage Interest',
            'Property Insurance',
            'Property Tax Assessments'
    ]
}

class GAAPClassifier:
    CLASSIFICATION = {
        "Assets": "Debit",
        "Liabilities": "Credit",
        "Equity": "Credit",
        "Revenue": "Credit",
        "Expenses": "Debit",
    }


TRANSACTION_CATEGORIES = {
    'Assets': {
        'account_types': ['Bank', 'Cash', 'Accounts Receivable'],
        'subcategories': {
            'Current Assets': ['Cash', 'Bank', 'Accounts Receivable', 'Prepaid Expenses'],
            'Fixed Assets': ['Property', 'Equipment', 'Furniture'],
            'Other Assets': ['Investments', 'Deposits']
        }
    },
    'Liabilities': {
        'account_types': ['Credit Card', 'Accounts Payable', 'Loans'],
        'subcategories': {
            'Current Liabilities': ['Credit Card', 'Accounts Payable', 'Short-term Loans'],
            'Long-term Liabilities': ['Mortgages', 'Long-term Loans'],
            'Other Liabilities': ['Deposits Held', 'Unearned Revenue']
        }
    },
    'Income': {
        'account_types': ['Bank', 'Cash'],
        'subcategories': {
            'Rental Income': ['Rent', 'Lease Payments'],
            'Other Income': ['Late Fees', 'Application Fees', 'Pet Rent'],
            'Investment Income': ['Interest', 'Dividends']
        }
    },
    'Expenses': {
        'account_types': ['Credit Card', 'Bank', 'Cash'],
        'subcategories': {
            'Operating Expenses': ['Utilities', 'Maintenance', 'Insurance'],
            'Administrative': ['Management Fees', 'Office Supplies', 'Professional Fees'],
            'Marketing': ['Advertising', 'Promotions'],
            'Financial': ['Bank Fees', 'Interest', 'Loan Payments']
        }
    }
}

# Maping 
FINANCIAL_EXPENSES_MAPPING = {
    'Bank Fees': 'Financial Expenses',
    'Credit Card Processing Fees': 'Financial Expenses',
    'Late Payment Penalties': 'Financial Expenses',
    'Loan Processing Fees': 'Financial Expenses',
    'Mortgage Interest': 'Financial Expenses',
    'Property Insurance': 'Financial Expenses',
    'Property Tax Assessments': 'Financial Expenses'
}



