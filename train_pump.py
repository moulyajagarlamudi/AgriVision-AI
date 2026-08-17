import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, confusion_matrix

# ===========================
# Load Dataset
# ===========================

df = pd.read_csv("dataset/AgriVision_training.csv")

# ===========================
# Input Features
# ===========================

X = df[
    [
        "Temperature",
        "Humidity",
        "Soil_Moisture",
        "Water_Level",
        "Air"
    ]
]

# ===========================
# Output
# ===========================

Y = df["Pump"]

# ===========================
# Train Test Split
# ===========================

X_train, X_test, Y_train, Y_test = train_test_split(
    X,
    Y,
    test_size=0.2,
    random_state=42
)

print("Training Samples :", len(X_train))
print("Testing Samples  :", len(X_test))

# ===========================
# Create AI Model
# ===========================

model = DecisionTreeClassifier(random_state=42)

# ===========================
# Train AI
# ===========================

model.fit(X_train, Y_train)

# ===========================
# Predictions
# ===========================

prediction = model.predict(X_test)

# ===========================
# Accuracy
# ===========================

accuracy = accuracy_score(Y_test, prediction)

print("\nAccuracy :", round(accuracy * 100, 2), "%")

# ===========================
# Confusion Matrix
# ===========================

print("\nConfusion Matrix")

print(confusion_matrix(Y_test, prediction))