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
        Downloads OHLCV data from Yahoo Finance
        """

        print(f"\nDownloading {self.ticker}...")

        df = yf.download(
            self.ticker,
            interval=self.interval,
            period=self.period,
            progress=False
        )

        if df.empty:
            raise Exception("Downloaded DataFrame is empty!")

        df.reset_index(inplace=True)

        return df

    def validate(self, df):
        """
        Validates downloaded data.
        """

        print("Validating data...")

        if df.isnull().sum().sum() > 0:
            print("Warning: Missing values detected!")

        if df.duplicated().sum() > 0:
            print("Warning: Duplicate rows found!")

        print("Validation Complete.")

    def save(self, df):
        """
        Saves data as CSV.
        """

        folder = "backend/data"

        os.makedirs(folder, exist_ok=True)

        filename = f"{self.ticker.replace('.', '_')}_{self.interval}.csv"

        path = os.path.join(folder, filename)

        df.to_csv(path, index=False)

        print(f"Data saved at:\n{path}")

    def run(self):
        df = self.download()
        self.validate(df)
        self.save(df)

        return df


if __name__ == "__main__":

    downloader = DataDownloader(
        ticker="RELIANCE.NS",
        interval="5m",
        period="60d"
    )

    data = downloader.run()

    print(data.head())