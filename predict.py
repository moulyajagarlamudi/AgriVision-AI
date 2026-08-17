import joblib
import pandas as pd

# Load trained AI model
model = joblib.load("Models/pump_model.pkl")

print("====================================")
print("      AGRIVISION AI PREDICTION")
print("====================================")

temperature = float(input("Temperature : "))
humidity    = float(input("Humidity    : "))
soil        = float(input("Soil Moisture : "))
water       = float(input("Water Level : "))
air         = int(input("Air Quality : "))

sample = pd.DataFrame([{
    "Temperature": temperature,
    "Humidity": humidity,
    "Soil_Moisture": soil,
    "Water_Level": water,
    "Air": air
}])

prediction = model.predict(sample)

print()

if prediction[0] == 1:
    print("✅ AI Decision : TURN ON WATER PUMP")
else:
    print("❌ AI Decision : KEEP WATER PUMP OFF")