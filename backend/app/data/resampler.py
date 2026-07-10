import os
import pandas as pd


class MultiTimeframeGenerator:

    def __init__(self, input_file):
        self.input_file = input_file

    def load_data(self):
        import os

        print("Current Working Directory:", os.getcwd())
        print("Input file:", self.input_file)
        print("Exists:", os.path.exists(self.input_file))
        df = pd.read_csv(self.input_file)

        # Convert datetime column
        df["Datetime"] = pd.to_datetime(df["Datetime"])

        df.set_index("Datetime", inplace=True)

        return df

    def resample(self, df, timeframe):

        resampled = df.resample(timeframe).agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        })

        resampled.dropna(inplace=True)

        return resampled

    def save(self, df, filename):

        os.makedirs("data/processed", exist_ok=True)

        path = os.path.join("data/processed", filename)

        df.to_csv(path)

        print(f"Saved: {path}")

    def run(self):

        df = self.load_data()

        timeframes = {
    "15min": "RELIANCE_NS_15m.csv",
    "30min": "RELIANCE_NS_30m.csv",
    "1h": "RELIANCE_NS_1H.csv",
    "4h": "RELIANCE_NS_4H.csv",
    "1D": "RELIANCE_NS_1D.csv"
        }

        for tf, filename in timeframes.items():

            new_df = self.resample(df, tf)

            self.save(new_df, filename)


if __name__ == "__main__":

    generator = MultiTimeframeGenerator(
        "data/raw/RELIANCE_NS_5m.csv"
    )

    generator.run()