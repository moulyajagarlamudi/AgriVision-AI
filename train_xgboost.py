import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix

from xgboost import XGBClassifier

# ==========================
# Load Dataset
# ==========================

df = pd.read_csv("dataset/AgriVision_training.csv")

# Features
X = df[
    [
        "Temperature",
        "Humidity",
        "Soil_Moisture",
        "Water_Level",
        "Air"
    ]
]

# Target
Y = df["Pump"]

# Train Test Split
X_train, X_test, Y_train, Y_test = train_test_split(
    X,
    Y,
    test_size=0.2,
    random_state=42
)

# XGBoost Model
model = XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    random_state=42,
    eval_metric="logloss"
)

# Train
model.fit(X_train, Y_train)

# Prediction
prediction = model.predict(X_test)

# Accuracy
accuracy = accuracy_score(Y_test, prediction)

print("\nAccuracy :", round(accuracy * 100, 2), "%")

print("\nConfusion Matrix")

print(confusion_matrix(Y_test, prediction))

# Save Model
joblib.dump(model, "Models/xgboost_model.pkl")

print("\nModel Saved Successfully!")