from pathlib import Path

import mplfinance as mpf
import pandas as pd


def load_data():

    project_root = Path(__file__).resolve().parents[3]

    csv_path = project_root / "data" / "processed" / "RELIANCE_NS_1H.csv"

    df = pd.read_csv(csv_path)

    df["Datetime"] = pd.to_datetime(df["Datetime"])

    df.set_index("Datetime", inplace=True)

    return df


def plot_chart():

    df = load_data()
    print(df.head())
    print(df.dtypes)

    mpf.plot(
        df,
        type="candle",
        style="charles",
        title="RELIANCE 1H Chart",
        volume=True,
        figsize=(14, 8),
    )


if __name__ == "__main__":
    plot_chart()