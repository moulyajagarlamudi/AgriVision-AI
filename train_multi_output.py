import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import accuracy_score

from xgboost import XGBClassifier

print("=" * 60)
print("      AGRIVISION MULTI-OUTPUT AI TRAINING")
print("=" * 60)

# ==========================================
# LOAD DATASET
# ==========================================

df = pd.read_csv("dataset/AgriVision_training.csv")

print("\nDataset Columns:")
print(df.columns)

# ==========================================
# REMOVE TIMESTAMP
# ==========================================

df = df.drop(columns=["timeStamp"])

# ==========================================
# ENCODE ZONE
# ==========================================

encoder = LabelEncoder()

df["Zone"] = encoder.fit_transform(df["Zone"])

# Save encoder for prediction later
joblib.dump(encoder, "Models/zone_encoder.pkl")

# ==========================================
# INPUT FEATURES
# ==========================================

X = df[
    [
        "Zone",
        "Temperature",
        "Humidity",
        "Soil_Moisture",
        "Air",
        "Water_Level"
    ]
]

# ==========================================
# OUTPUT LABELS
# ==========================================

Y = df[["Pump", "Fan"]]

# ==========================================
# TRAIN TEST SPLIT
# ==========================================

X_train, X_test, Y_train, Y_test = train_test_split(
    X,
    Y,
    test_size=0.20,
    random_state=42,
    stratify=Y["Pump"]   # optional
)

# ==========================================
# MODEL
# ==========================================

model = MultiOutputClassifier(
    XGBClassifier(
        random_state=42,
        eval_metric="logloss"
    )
)

print("\nTraining AI Model...\n")

model.fit(X_train, Y_train)

# ==========================================
# PREDICTION
# ==========================================

prediction = model.predict(X_test)



# ==========================================
# SAVE MODEL
# ==========================================

joblib.dump(model, "Models/agri_ai_model.pkl")

print("\nModel Saved Successfully!")
print("Model      : Models/agri_ai_model.pkl")
print("Encoder    : Models/zone_encoder.pkl")