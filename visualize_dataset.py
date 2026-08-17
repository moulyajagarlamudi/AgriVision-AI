import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("dataset/AgriVision_training.csv")

df.hist(figsize=(12, 8))

plt.show()
