# Main categories
MAIN_CATEGORIES = [
    "Assets",
    "Liabilities",
    "Equity",
    "Revenue",
    "Expenses"
]
# Update SUBCATEGORIES to match
SUBCATEGORIES = {
    "Assets": [
        "Current Assets",
        "Non-Current Assets"
    ],
    "Liabilities": [
        "Current Liabilities",
        "Current Liabilities (Unearned Revenue)",
        "Non-Current Liabilities (Long-Term Debt)"
    ],
    "Equity": [
        "Retained Earnings (Current Year)",
        "Owner's Withdrawals",
        "Contributed Capital",
        "Retained Earnings (Accumulated)"
    ],
    "Revenue": [
        "Rental Income",
        "Other Revenue"
    ],
    "Expenses": [
        "Operating Expenses (Administrative)",
        "Operating Expenses (Insurance)",
        "Operating Expenses (Professional Fees)",
        "Operating Expenses (Repairs and Maintenance)",
        "Operating Expenses (Marketing)",
        "Operating Expenses (Property Taxes)",
        "Operating Expenses (Security)",
        "Operating Expenses (Utilities)",
        "Operating Expenses (Common Area)",
        "Operating Expenses (Rent)",
        "Financial Expenses",
        "Interest Expenses"
    ]
}

ACCOUNTS = {
    # Asset Accounts
    "CURRENT ASSETS": [
        "Accounts Receivable",
        "Prepaid Rent",
        "Prepaid Insurance"
    ],

    "NON-CURRENT ASSETS": [
        "Property, Plant, and Equipment",
        "Leasehold Improvements"
    ],

    # Liability Accounts
    "CURRENT LIABILITIES": [
        "Mortgage Payable",
        "Unearned Rent",
        "Accounts Payable",
        "Deferred Revenue",
        "Long-Term Debt"
    ],

    "NON-CURRENT LIABILITIES": [
        "Long-Term Debt"
    ],

    # Equity Accounts
    "EQUITY": [
        "Retained Earnings (Current Year)",
        "Owner's Withdrawals",
        "Contributed Capital",
        "Retained Earnings (Accumulated)"
    ],

    # Revenue Accounts
    "REVENUE": [
        "Rental Income",
        "Other Revenue"
    ],

    # Expense Accounts
    "ADMINISTRATIVE EXPENSES": [
        "Administrative Expenses",
        "Property Management Fees"
    ],

    "INSURANCE": [
        "Insurance",
        "Property Insurance"
    ],

    "PROFESSIONAL FEES": [
        "Legal and Professional Fees"
    ],

    "REPAIRS AND MAINTENANCE": [
        "Maintenance and Repairs",
        "Pest Control",
        "HVAC Maintenance",
        "Elevator Maintenance",
        "Lobby Maintenance",
        "Parking Lot Maintenance"
    ],

    "MARKETING EXPENSES": [
        "Marketing and Advertising",
        "Signage"
    ],

    "PROPERTY_TAXES": [
        "Property Taxes",
        "Property Tax Assessments"
    ],

    "SECURITY": [
        "Security Services",
        "Security Systems"
    ],

    "UTILITIES": [
        "Utilities",
        "Common Area Utilities",
        "Lighting",
        "Waste Management"
    ],

    "COMMON AREA EXPENSES": [
        "Cleaning Services",
        "Common Area Maintenance (CAM)",
        "Landscaping",
        "Snow Removal"
    ],


    "FINANCIAL EXPENSES": [
        "Bank Fees",
        "Credit Card Processing Fees",
        "Late Payment Penalties",
        "Loan Processing Fees",
        "Mortgage Interest"
    ]
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
    'Expenses': {
        'Operating Expenses': [
            'Administrative Expenses',
            'Insurance',
            'Legal and Professional Fees',
            'Maintenance and Repairs',
            'Marketing and Advertising',
            'Pest Control',
            'Property Management Fees',
            'Property Taxes',
            'Security Services',
            'Utilities'
        ],
        'Common Area Expenses': [
            'Common Area Maintenance (CAM)',
            'Common Area Utilities',
            'Landscaping',
            'Lighting',
            'Lobby Maintenance',
            'Parking Lot Maintenance',
            'Security Systems',
            'Signage',
            'Snow Removal'
        ],
        'Occupancy Expenses': [
            'Cleaning Services',
            'Elevator Maintenance',
            'Maintenance and Repairs',
            'Lease Payments',
            'Rent',
            'Tenant Improvements',
            'Waste Management'
        ],
        'Financial Expenses': [
            'Bank Fees',
            'Credit Card Processing Fees',
            'Late Payment Penalties',
            'Loan Processing Fees',
            'Mortgage Interest',
            'Property Insurance',
            'Property Tax Assessments'
        ]
    }
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


