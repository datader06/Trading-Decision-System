"""
swings.py
=========
SwingDetector identifies local swing highs and swing lows using a
rolling-window pivot approach, then scores each swing point for quality.

Swing Quality Score (0–100) is based on:
    - Prominence : number of confirming bars on each side (25 pts)
    - ATR ratio  : swing size relative to current ATR (50 pts)
    - Volume     : volume at the swing relative to rolling average (25 pts)

If volume data is unavailable, that component defaults to 50/100.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


class SwingDetector:
    """
    Detects swing highs and swing lows with optional quality scoring.

    Args:
        window   : Number of bars required on each side of a swing point.
        atr_period: Period for ATR calculation used in quality scoring.
    """

    def __init__(
        self,
        csv_path: Optional[str] = None,
        window: int = 2,
        atr_period: int = 14,
    ) -> None:
        self.csv_path   = Path(csv_path) if csv_path else None
        self.window     = window
        self.atr_period = atr_period

    # ─────────────────────────────────────────────────────────────────
    def load_data(self) -> pd.DataFrame:
        """Load OHLCV data from CSV."""
        if self.csv_path is None:
            raise ValueError("csv_path must be set before calling load_data().")
        df = pd.read_csv(self.csv_path)
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        return df

    # ─────────────────────────────────────────────────────────────────
    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        """Compute ATR using Wilder's method."""
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"].shift(1)

        tr = pd.concat(
            [high - low, (high - close).abs(), (low - close).abs()], axis=1
        ).max(axis=1)

        atr = tr.ewm(alpha=1 / self.atr_period, min_periods=self.atr_period, adjust=False).mean()
        return atr

    # ─────────────────────────────────────────────────────────────────
    def _swing_quality(
        self,
        df: pd.DataFrame,
        idx: int,
        swing_type: str,   # "High" or "Low"
        atr: pd.Series,
    ) -> float:
        """
        Score a swing point on a 0–100 scale.

        Components:
            prominence_score (0–25):  confirmations on each side
            atr_score        (0–50):  swing magnitude vs ATR
            volume_score     (0–25):  volume at swing vs rolling mean
        """
        n      = len(df)
        w      = self.window
        price_col = "High" if swing_type == "High" else "Low"

        # ── 1. Prominence ──────────────────────────────────────────
        left_bars  = min(idx, 5)
        right_bars = min(n - idx - 1, 5)
        prominence_score = round(((left_bars + right_bars) / 10) * 25)

        # ── 2. ATR ratio ───────────────────────────────────────────
        atr_val = atr.iloc[idx] if not np.isnan(atr.iloc[idx]) else 0.0
        if atr_val > 0:
            swing_price = df[price_col].iloc[idx]
            if swing_type == "High":
                neighbors = df["Low"].iloc[max(0, idx - w): idx + w + 1]
                move = swing_price - neighbors.min()
            else:
                neighbors = df["High"].iloc[max(0, idx - w): idx + w + 1]
                move = neighbors.max() - swing_price
            ratio = move / atr_val
            atr_score = round(min(ratio / 3.0, 1.0) * 50)   # caps at 3× ATR
        else:
            atr_score = 25

        # ── 3. Volume ──────────────────────────────────────────────
        if "Volume" in df.columns and df["Volume"].sum() > 0:
            vol_window = 20
            start = max(0, idx - vol_window)
            avg_vol = df["Volume"].iloc[start:idx].mean()
            if avg_vol > 0:
                vol_ratio = df["Volume"].iloc[idx] / avg_vol
                volume_score = round(min(vol_ratio / 2.0, 1.0) * 25)
            else:
                volume_score = 12
        else:
            volume_score = 12    # neutral when volume unavailable

        return float(min(prominence_score + atr_score + volume_score, 100))

    # ─────────────────────────────────────────────────────────────────
    def detect_swings(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect swing highs and lows, and score each swing point.

        Adds columns to df:
            Swing_High       (bool)
            Swing_Low        (bool)
            Swing_Strength   (float 0–100, 0 for non-swing rows)
        """
        df = df.copy()
        df["Swing_High"]     = False
        df["Swing_Low"]      = False
        df["Swing_Strength"] = 0.0

        atr = self._compute_atr(df)
        highs = df["High"]
        lows  = df["Low"]
        w     = self.window

        for i in range(w, len(df) - w):

            # ── Swing High ─────────────────────────────────────────
            if highs.iloc[i] == highs.iloc[i - w: i + w + 1].max():
                quality = self._swing_quality(df, i, "High", atr)
                df.iat[i, df.columns.get_loc("Swing_High")]     = True
                df.iat[i, df.columns.get_loc("Swing_Strength")] = quality

            # ── Swing Low ──────────────────────────────────────────
            elif lows.iloc[i] == lows.iloc[i - w: i + w + 1].min():
                quality = self._swing_quality(df, i, "Low", atr)
                df.iat[i, df.columns.get_loc("Swing_Low")]      = True
                df.iat[i, df.columns.get_loc("Swing_Strength")] = quality

        return df

    # ─────────────────────────────────────────────────────────────────
    def run(self) -> pd.DataFrame:
        """Load CSV and detect swings. Convenience entry point."""
        df = self.load_data()
        return self.detect_swings(df)

    # ─────────────────────────────────────────────────────────────────
    def run_on_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect swings on a pre-loaded DataFrame (for pipeline use)."""
        return self.detect_swings(df)


# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    detector = SwingDetector("data/processed/RELIANCE_NS_1H.csv")
    result   = detector.run()
    swings   = result[result["Swing_High"] | result["Swing_Low"]]
    print(swings[["Datetime", "High", "Low", "Swing_High", "Swing_Low", "Swing_Strength"]].head(20))