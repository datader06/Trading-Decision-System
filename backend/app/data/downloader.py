import os
import pandas as pd
import yfinance as yf


class DataDownloader:
    def __init__(self, ticker, interval, period):
        self.ticker = ticker
        self.interval = interval
        self.period = period

    def download(self):
        """
        Downloads OHLCV data from Yahoo Finance.
        """

        print(f"\nDownloading {self.ticker}...")

        df = yf.download(
            self.ticker,
            interval=self.interval,
            period=self.period,
            progress=False,
            auto_adjust=False
        )

        if df.empty:
            raise Exception("Downloaded DataFrame is empty!")

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Reset index so Datetime becomes a column
        df.reset_index(inplace=True)
        # Remove Adj Close if present
        if "Adj Close" in df.columns:
            df.drop(columns=["Adj Close"], inplace=True)

        # Reorder columns
        df = df[
    [
        "Datetime",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]
]

        return df

    def validate(self, df):
        """
        Validate downloaded data.
        """

        print("\nValidating data...")

        required_columns = [
            "Datetime",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for col in required_columns:
            if col not in df.columns:
                raise Exception(f"Missing column: {col}")

        # Convert numeric columns
        numeric_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Remove rows containing NaN
        df.dropna(inplace=True)

        # Remove duplicate rows
        df.drop_duplicates(inplace=True)

        print("Validation Complete.")
        print(f"Rows: {len(df)}")

        return df

    def save(self, df):
        """
        Save cleaned data.
        """

        folder = "data/raw"

        os.makedirs(folder, exist_ok=True)

        filename = f"{self.ticker.replace('.', '_')}_{self.interval}.csv"

        path = os.path.join(folder, filename)

        df.to_csv(path, index=False)

        print(f"\nData saved successfully:")
        print(path)

    def run(self):

        df = self.download()

        df = self.validate(df)

        self.save(df)

        return df


if __name__ == "__main__":

    downloader = DataDownloader(
        ticker="RELIANCE.NS",
        interval="5m",
        period="60d"
    )

    df = downloader.run()

    print("\nPreview:")
    print(df.head())

    print("\nData Types:")
    print(df.dtypes)