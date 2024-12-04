from sklearn.ensemble import RandomForestClassifier
import joblib
import os

def create_basic_model():
    try:
        # Create a basic model
        model = RandomForestClassifier(n_estimators=100)
        
        # Define the path
        model_path = os.path.join(
            os.path.dirname(__file__),
            'models',
            'expense_classifier.joblib'
        )
        
        # Save the model
        joblib.dump(model, model_path)
        print(f"Successfully created model at: {model_path}")
        
    except Exception as e:
        print(f"Error creating model: {e}")

if __name__ == "__main__":
    create_basic_model() 