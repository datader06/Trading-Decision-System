import os
import pandas as pd

from backend.app.market_structure.swings import SwingDetector


class MarketStructure:
    """
    Detects and classifies market structure from swing points.

    Output:
        1. Full OHLC DataFrame with Structure column.
        2. Structure DataFrame containing only significant swing points.
    """

    def __init__(self, csv_path):
        self.csv_path = csv_path

    def build(self):
        """
        Build market structure by classifying swings into:

            SH  = Swing High
            SL  = Swing Low
            HH  = Higher High
            HL  = Higher Low
            LH  = Lower High
            LL  = Lower Low
        """

        detector = SwingDetector(self.csv_path)
        df = detector.run()

        df["Structure"] = None

        structure_points = []

        last_high = None
        last_low = None

        for idx, row in df.iterrows():

            # =====================================
            # Swing High
            # =====================================
            if row["Swing_High"]:

                if last_high is None:
                    structure = "SH"

                elif row["High"] > last_high:
                    structure = "HH"

                else:
                    structure = "LH"

                last_high = row["High"]

                df.at[idx, "Structure"] = structure

                structure_points.append(
                    {
                        "Index": idx,
                        "Datetime": row["Datetime"],
                        "Swing_Type": "High",
                        "Price": row["High"],
                        "Structure": structure,
                    }
                )

            # =====================================
            # Swing Low
            # =====================================
            elif row["Swing_Low"]:

                if last_low is None:
                    structure = "SL"

                elif row["Low"] > last_low:
                    structure = "HL"

                else:
                    structure = "LL"

                last_low = row["Low"]

                df.at[idx, "Structure"] = structure

                structure_points.append(
                    {
                        "Index": idx,
                        "Datetime": row["Datetime"],
                        "Swing_Type": "Low",
                        "Price": row["Low"],
                        "Structure": structure,
                    }
                )

        structure_df = pd.DataFrame(structure_points)

        return df, structure_df

    def save_structure(self, structure_df):
        """
        Save structure table.
        """

        output_folder = "data/processed"
        os.makedirs(output_folder, exist_ok=True)

        output_file = os.path.join(
            output_folder,
            "RELIANCE_NS_1H_structure.csv"
        )

        structure_df.to_csv(output_file, index=False)

        print(f"\nStructure table saved to:\n{output_file}")

    def summary(self, structure_df):
        """
        Print summary.
        """

        print("\n========== Market Structure Summary ==========\n")

        print(structure_df["Structure"].value_counts())

        print("\nTotal Swing Points:", len(structure_df))

        print("\n==============================================\n")


if __name__ == "__main__":

    ms = MarketStructure(
        "data/processed/RELIANCE_NS_1H.csv"
    )

    df, structure_df = ms.build()

    ms.summary(structure_df)

    ms.save_structure(structure_df)

    print(structure_df.head(15))
