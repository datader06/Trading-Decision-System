import pandas as pd

df = pd.read_csv("data/raw/RELIANCE_NS_5m.csv")

print(df.head())
print(df.dtypes)
print(df["Volume"].head(10))