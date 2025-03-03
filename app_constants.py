MAIN_CATEGORIES = {
    "Assets": ["Current Asset", "Non-Current Asset"],
    "Liabilities": ["Current Liability", "Non-Current Liability"],
    "Equity": ["Equity"],
    "Revenue": ["Income", "Other Income"],  # Added "Other Income"
    "Cost of Sales": ["Cost of Sales"
        "Maintenance and Repairs Expenses",
        "Property Management Expenses",
        "Insurance Expenses",
        "Pest Control Expenses",
        "Utilities",
        "Property Taxes",
        "Property Tax Assessments",
        "Property Expense", 

],  # Added "Cost of Sales"
    "Expenses": [
        "Administrative Expenses",
        "Operating Expenses", # Create
        "Oerating Expenses",
        "Financial Expenses",
        "Marketing Expenses",  # Added "Insurance"
        "Legal and Professional Fees",  # Added "Legal and Professional Fees"
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
        "Other Revenue": ("Revenue", "Other Income"),
        "Parking Fees": ("Revenue", "Income"),
        "Pet Fees": ("Revenue", "Other Income"), 
        "Property Management Fees": ("Expenses", "Administrative Expenses"),
        "Property Insurance": ("Expenses", "Administrative Expenses"), 
        "Pest Control": ("Expenses", "Administrative Expenses"),
        "Signage": ("Expenses", "Administrative Expenses"),
        "Lighting": ("Cost of Sales", "Utilities"),
        "Waste Management": ("Cost of Sales", "Utilities"),
        "HVAC Maintenance": ("Cost of Sales", "Utilities"),
        "Common Area Utilities": ("Expenses", "Common Area Expenses"),
        "Landscaping": ("Cost of Sales", "Common Area Expenses"),
        "Snow Removal": ("Cost of Sales", "Property Expenses"),
        "Bank Fees": ("Expenses", "Financial Expenses"),
        "Credit Card Processing Fees": ("Expenses", "Financial Expenses"),
        "Loan Processing Fees": ("Expenses", "Financial Expenses"),
        "Marketing and Advertising": ("Expenses", "Marketing Expenses"),
        "Elevator Maintenance": ("Expenses", "Property Management Expenses"),
        "Lobby Maintenance": ("Cost of Sales", "Property Management Expenses"),
        "Parking Lot Maintenance": ("Expenses", "Property Management Expenses"),
        "Building": ("Assets", "Non-Current Asset"),
        "Equipment": ("Assets", "Non-Current Asset"),
        "Furniture and Fixtures": ("Assets", "Non-Current Asset"),
        "Land": ("Assets", "Non-Current Asset"),
        "Prepaid Expenses": ("Assets", "Current Asset"),  
        "Maintenance Reserves": ("Liabilities", "Current Liability"), 
        "Property Tax Payable": ("Liabilities", "Current Liability"),
        "Security Deposits": ("Liabilities", "Current Liability"), 
        "Application Fees": ("Revenue", "Other Income"),
        "Common Area Revenue": ("Revenue", "Other Income"),
        "Late Fee Income": ("Revenue", "Other Income"),
        "Storage Unit Rental": ("Revenue", "Income"),
        "Utility Reimbursements": ("Revenue", "Income"),
        "Administrative Expenses": ("Expenses", "Administrative Expenses"), 
        "Insurance": ("Expenses", "Insurance"),  
        "Legal and Professional Fees": ("Expenses", "Legal and Professional Fees"), 
        "Maintenance and Repairs": ("Expenses", "Maintenance and Repairs"), 
        "Property Taxes": ("Expenses", "Property Taxes"), 
        "Security Services": ("Expenses", "Security Services"), 
        "Utilities": ("Expenses", "Utilities"),  
        "Cleaning Services": ("Expenses", "Cleaning Services"),  
        "Tenant Improvements": ("Assets", "Non-Current Asset"), 
        "Late Payment Penalties": ("Revenue", "Other Income"),  
        "Mortgage Interest": ("Expenses", "Financial Expenses"), 
        "Property Tax Assessments": ("Expenses", "Property Taxes"),
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
    'Assets': {
        'Current Assets': [
            'Accounts Receivable',
            'Prepaid Expenses',
            'Prepaid Insurance',
            'Prepaid Rent',
            'Bank'
        ],
        
        'Non-Current Assets': [
            'Building',
            'Equipment',
            'Furniture and Fixtures',
            'Land',
            'Leasehold Improvements',
            'Tenant Improvements'  
        ]
    },
    'Liabilities': {
        'Current Liabilities': [
            'Accounts Payable',
            'Accrued Expenses',
            'Deferred Revenue',
            'Maintenance Reserves', 
            'Property Tax Payable',
            'Security Deposits',
            'Unearned Rent'
            'Short-Term Loan'
        ],
        'Non-Current Liabilities': [
            'Long-Term Debt',
            'Mortgage Payable',
            'Account Payable'
            'Long-Term Loan'

        ]
    },
    'Equity': [ 
        'Contributed Capital',
        'Current Year Earnings',
        'Distributions',
        "Owner's Capital",
        "Owner's Withdrawals",
        'Partner Contributions',
        'Retained Earnings',
        'Retained Earnings (Accumulated)',
        'Retained Earnings (Current Year)'
    ],
    'Revenue': {
        'Rental Income': [ 
            'Rental Income',
            'Parking Fees', 
            'Storage Unit Rental',
        ],
        'Other Income': [ 
            'Application Fees',
            'Common Area Revenue',
            'Late Fee Income',
            'Late Payment Penalties', 
            'Other Revenue',
            'Pet Rent', 
            'Utility Reimbursements' 
        ]
    },
    'Expenses': {
        'Operating Expenses': [ 
            'Administrative Expenses',
            'Legal and Professional Fees',
            'Marketing and Advertising',  
            'Property Management Fees', 
            'Security Systems',
            'Landscaping',
            'Levies',
            'Home Owners Association Fees',
        ],
        'Maintenance and Repairs Expenses': [
            'Maintenance and Repairs',
            'Common Area Maintenance (CAM)', 
            'Elevator Maintenance',
            'Parking Lot Maintenance' 
        ],
        'Financial Expenses': [
            'Bank Fees',
            'Credit Card Processing Fees',
            'Loan Processing Fees', 
            'Mortgage Interest' 
        ],
        'Cost of Sales': [  
            'Property Taxes',
            'Property Tax Assessments',
            'Pest Control', 
            'Snow Removal',
            'Cleaning Services',
            'Waste Management' 
        ],
        'Insurance Expenses': [
            'Insurance',
            'Property Insurance'
        ],
        'Staff Expenses': [
            'Property Manager',
            'Cleaning Staff',
            'Security Guard',
            'Receptionist'
        ],
        'Utilities': [  
            'Utilities',
            'Common Area Utilities',
            'Lighting'
        ],
        'Depreciation & Amortization': [
            'Depreciation',
            'Amortization'
        ]
    }
}

class GAAPClassifier:
    CLASSIFICATION = {
        "Assets": "Debit",
        "Liabilities": "Credit",
        "Equity": "Credit",
        "Revenue": "Credit",
        "Expenses": "Debit",
    }

