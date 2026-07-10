from pathlib import Path

import pandas as pd

from backend.app.market_structure.swings import SwingDetector


class MarketStructure:

    def __init__(self, csv_path):
        self.csv_path = csv_path

    def build(self):

        detector = SwingDetector(self.csv_path)

        df = detector.run()

        df["Structure"] = None

        last_high = None
        last_low = None

        for idx, row in df.iterrows():

            # Swing High
            if row["Swing_High"]:

                if last_high is None:
                    df.at[idx, "Structure"] = "SH"

                else:

                    if row["High"] > last_high:
                        df.at[idx, "Structure"] = "HH"

                    else:
                        df.at[idx, "Structure"] = "LH"

                last_high = row["High"]

            # Swing Low
            elif row["Swing_Low"]:

                if last_low is None:
                    df.at[idx, "Structure"] = "SL"

                else:

                    if row["Low"] > last_low:
                        df.at[idx, "Structure"] = "HL"

                    else:
                        df.at[idx, "Structure"] = "LL"

                last_low = row["Low"]

        return df


if __name__ == "__main__":

    ms = MarketStructure(
        "data/processed/RELIANCE_NS_1H.csv"
    )

    df = ms.build()

    print(df[df["Structure"].notna()][
        ["Datetime",
         "High",
         "Low",
         "Structure"]
    ])