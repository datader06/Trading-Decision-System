"""
resampler.py
============
MultiTimeframeGenerator downloads raw OHLCV data and resamples it
into multiple timeframes required for the MTF analysis pipeline.

Usage:
    gen = MultiTimeframeGenerator(ticker="RELIANCE.NS")
    tf_data = gen.run(raw_df)   # returns dict[str, pd.DataFrame]
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from backend.app.core.timeframe import Timeframe


class MultiTimeframeGenerator:
    """
    Resamples a raw 5-minute OHLCV DataFrame into every analysis timeframe.

    Args:
        ticker    : Ticker symbol (used for file naming only).
        timeframes: List of Timeframe members to generate.
                    Defaults to all five standard timeframes.
        save_dir  : Directory to save CSVs.  Pass None to skip saving.
    """

    DEFAULT_TIMEFRAMES = Timeframe.ordered()   # D1 → H4 → H1 → M15 → M5

    def __init__(
        self,
        ticker: str = "TICKER",
        timeframes: Optional[list] = None,
        save_dir: Optional[str] = "data/processed",
    ) -> None:
        self.ticker     = ticker
        self.timeframes = timeframes or self.DEFAULT_TIMEFRAMES
        self.save_dir   = save_dir

    # ─────────────────────────────────────────────────────────────────
    def load_csv(self, input_file: str) -> pd.DataFrame:
        """Load a raw OHLCV CSV into a datetime-indexed DataFrame."""
        df = pd.read_csv(input_file)
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df.set_index("Datetime", inplace=True)
        return df

    # ─────────────────────────────────────────────────────────────────
    def resample(self, df: pd.DataFrame, timeframe: Timeframe) -> pd.DataFrame:
        """Resample a DataFrame to the given Timeframe."""
        resampled = df.resample(timeframe.resample_str).agg(
            {
                "Open":   "first",
                "High":   "max",
                "Low":    "min",
                "Close":  "last",
                "Volume": "sum",
            }
        )
        resampled.dropna(inplace=True)
        return resampled

    # ─────────────────────────────────────────────────────────────────
    def _save(self, df: pd.DataFrame, timeframe: Timeframe) -> None:
        """Persist a resampled DataFrame to CSV."""
        if self.save_dir is None:
            return
        os.makedirs(self.save_dir, exist_ok=True)
        safe_ticker = self.ticker.replace(".", "_")
        filename = f"{safe_ticker}_{timeframe.name}.csv"
        path = os.path.join(self.save_dir, filename)
        df.to_csv(path)
        print(f"  Saved {timeframe.display_name:10s} → {path}")

    # ─────────────────────────────────────────────────────────────────
    def run(self, raw_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """
        Generate all configured timeframes from a raw OHLCV DataFrame.

        Args:
            raw_df: Raw OHLCV data (must be datetime-indexed).

        Returns:
            Dictionary keyed by Timeframe.resample_str  e.g. {"1h": df, "4h": df, ...}
        """
        results: dict[str, pd.DataFrame] = {}

        print(f"\nGenerating {len(self.timeframes)} timeframes for {self.ticker}...")

        for tf in self.timeframes:
            resampled = self.resample(raw_df, tf)
            results[tf.resample_str] = resampled
            self._save(resampled, tf)

        print("Done.\n")
        return results

    # ─────────────────────────────────────────────────────────────────
    def run_from_csv(self, input_file: str) -> dict[str, pd.DataFrame]:
        """Convenience wrapper: load CSV then generate all timeframes."""
        raw_df = self.load_csv(input_file)
        return self.run(raw_df)