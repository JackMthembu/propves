from sklearn.ensemble import RandomForestClassifier
import joblib
import os

def train_and_save_model():
    try:
        # Create a basic model (replace with your actual training code)
        model = RandomForestClassifier()
        
        # Train your model here
        # model.fit(X_train, y_train)
        
        # Create models directory if it doesn't exist
        model_dir = os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(model_dir, exist_ok=True)
        
        # Save the model
        model_path = os.path.join(model_dir, 'expense_classifier.joblib')
        joblib.dump(model, model_path)
        print(f"Model saved to {model_path}")
        
    except Exception as e:
        print(f"Error training/saving model: {e}")

if __name__ == "__main__":
    train_and_save_model() 