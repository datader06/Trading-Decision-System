from pathlib import Path

import pandas as pd


class SwingDetector:
    def __init__(self, csv_path, window=2):
        self.csv_path = Path(csv_path)
        self.window = window

    def load_data(self):
        df = pd.read_csv(self.csv_path)

        df["Datetime"] = pd.to_datetime(df["Datetime"])

        return df

    def detect_swings(self, df):

        df["Swing_High"] = False
        df["Swing_Low"] = False

        highs = df["High"]
        lows = df["Low"]

        for i in range(self.window, len(df) - self.window):

            # Swing High
            if highs.iloc[i] == max(
                highs.iloc[i-self.window:i+self.window+1]
            ):
                df.loc[i, "Swing_High"] = True

            # Swing Low
            if lows.iloc[i] == min(
                lows.iloc[i-self.window:i+self.window+1]
            ):
                df.loc[i, "Swing_Low"] = True

        return df

    def run(self):

        df = self.load_data()

        df = self.detect_swings(df)

        return df


if __name__ == "__main__":

    detector = SwingDetector(
        "data/processed/RELIANCE_NS_1H.csv"
    )

    df = detector.run()

    print(df[df["Swing_High"] | df["Swing_Low"]].head(20))
    