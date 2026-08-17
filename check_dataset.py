import pandas as pd

df = pd.read_csv("dataset/AgriVision_training.csv")

print("=================================")
print("      AGRIVISION DATASET")
print("=================================")

print("\nFirst 5 Rows\n")
print(df.head())

print("\n---------------------------------")

print("Dataset Shape")
print(df.shape)

print("\n---------------------------------")

print("Column Names")
print(df.columns)

print("\n---------------------------------")

print("Missing Values")
print(df.isnull().sum())

print("\n---------------------------------")

print("Data Types")
print(df.dtypes)

print("\n=================================")