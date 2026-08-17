import pandas as pd
import time

from sklearn.model_selection import train_test_split

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

# -----------------------------------
# Load Dataset
# -----------------------------------

df = pd.read_csv("dataset/AgriVision_training.csv")

X = df[
    [
        "Temperature",
        "Humidity",
        "Soil_Moisture",
        "Water_Level",
        "Air"
    ]
]

Y = df["Pump"]

X_train, X_test, Y_train, Y_test = train_test_split(
    X,
    Y,
    test_size=0.2,
    random_state=42
)

models = {
    "Decision Tree": DecisionTreeClassifier(random_state=42),

    "Random Forest": RandomForestClassifier(
        n_estimators=100,
        random_state=42
    ),

    "XGBoost": XGBClassifier(
        eval_metric="logloss",
        random_state=42
    )
}

print("=" * 70)
print("        AGRIVISION MODEL COMPARISON")
print("=" * 70)

for name, model in models.items():

    start = time.time()

    model.fit(X_train, Y_train)

    end = time.time()

    prediction = model.predict(X_test)

    accuracy = accuracy_score(Y_test, prediction)

    precision = precision_score(Y_test, prediction)

    recall = recall_score(Y_test, prediction)

    f1 = f1_score(Y_test, prediction)

    print()

    print(name)

    print("-" * 40)

    print("Accuracy  :", round(accuracy * 100, 2), "%")

    print("Precision :", round(precision * 100, 2), "%")

    print("Recall    :", round(recall * 100, 2), "%")

    print("F1 Score  :", round(f1 * 100, 2), "%")

    print("Training Time :", round(end - start, 4), "seconds")