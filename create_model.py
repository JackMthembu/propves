from sklearn.ensemble import RandomForestClassifier
import joblib
import numpy as np

# Create a simple initial model
clf = RandomForestClassifier(n_estimators=100, random_state=42)

# Create some dummy training data
# Replace this with your actual training data when available
X_train = np.random.rand(100, 10)  # 100 samples, 10 features
y_train = np.random.randint(0, 3, 100)  # 3 classes

# Train the model
clf.fit(X_train, y_train)

# Save the model
joblib.dump(clf, 'models/expense_classifier.joblib') 