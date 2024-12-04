import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
import joblib

def prepare_training_data():
    """
    Prepare training data from your expense records
    """
    # Example structure - modify based on your actual data
    data = pd.DataFrame({
        'description': ['electricity bill', 'water charges', 'Association Fees', ...],
        'category': ['electricity', 'water_sewer', 'hoa_fees', ...]
    })
    
    return data

def train_expense_classifier():
    # Load and prepare data
    data = prepare_training_data()
    
    # Split into features (X) and target (y)
    X = data['description']
    y = data['category']
    
    # Split into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Create pipeline
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            lowercase=True,
            max_features=5000,
            stop_words='english'
        )),
        ('classifier', RandomForestClassifier(
            n_estimators=100,
            random_state=42
        ))
    ])
    
    # Train the model
    print("Training model...")
    pipeline.fit(X_train, y_train)
    
    # Evaluate the model
    print("\nModel Performance:")
    y_pred = pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))
    
    # Save the model
    model_path = 'models/expense_classifier.joblib'
    joblib.dump(pipeline, model_path)
    print(f"\nModel saved to {model_path}")
    
    return pipeline

if __name__ == "__main__":
    model = train_expense_classifier() 