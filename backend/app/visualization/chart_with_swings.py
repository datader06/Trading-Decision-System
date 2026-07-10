from pathlib import Path

import mplfinance as mpf
import pandas as pd

from backend.app.market_structure.swings import SwingDetector


def plot_swings():

    detector = SwingDetector(
        "data/processed/RELIANCE_NS_1H.csv"
    )

    df = detector.run()

    df["Datetime"] = pd.to_datetime(df["Datetime"])
    df.set_index("Datetime", inplace=True)

    swing_high = df["High"].where(df["Swing_High"])
    swing_low = df["Low"].where(df["Swing_Low"])

    apds = [
        mpf.make_addplot(
            swing_high,
            type="scatter",
            marker="^",
            markersize=80,
        ),
        mpf.make_addplot(
            swing_low,
            type="scatter",
            marker="v",
            markersize=80,
        ),
    ]

    mpf.plot(
        df,
        type="candle",
        style="charles",
        addplot=apds,
        volume=True,
        figsize=(16, 8),
        title="Market Structure - Swing Detection",
    )


if __name__ == "__main__":
    plot_swings()