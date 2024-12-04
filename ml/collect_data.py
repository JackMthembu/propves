import pandas as pd
from datetime import datetime
import os
from ml.predict import classify_expense


def log_training_example(text, category, confidence, is_correct=True):
    """Log expense classifications for model training"""
    example = {
        'description': text,
        'category': category,
        'confidence': confidence,
        'is_correct': is_correct,
        'timestamp': datetime.now()
    }
    
    filepath = 'ml/data/training_examples.csv'
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        df = pd.DataFrame(columns=['description', 'category', 'confidence', 'is_correct', 'timestamp'])
    
    df = pd.concat([df, pd.DataFrame([example])], ignore_index=True)
    df.to_csv(filepath, index=False)

# Add this to your expense processing code
def process_expense(description, amount):
    classification = classify_expense(description)
    if classification:
        # Log successful classifications for training
        log_training_example(
            text=description,
            category=classification['category'],
            confidence=classification['confidence']
        ) 