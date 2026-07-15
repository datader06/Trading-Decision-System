"""
test_swing_detector.py
======================
Unit tests for SwingDetector.
"""

import pandas as pd
import numpy as np
import pytest

from backend.app.market_structure.swings import SwingDetector


# ── Fixtures ──────────────────────────────────────────────────────────

def make_simple_df(n: int = 30) -> pd.DataFrame:
    """Generate a simple trending-up OHLCV DataFrame."""
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "Datetime": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "Open":     prices - 0.1,
        "High":     prices + 0.5,
        "Low":      prices - 0.5,
        "Close":    prices,
        "Volume":   np.random.randint(1000, 5000, n).astype(float),
    })
    return df


def make_clear_swings_df() -> pd.DataFrame:
    """DataFrame with manually defined swing highs/lows."""
    #  create a zigzag: up-down-up-down
    rows = []
    pattern = [10, 12, 9, 13, 8, 14, 7, 15]
    for i, p in enumerate(pattern):
        rows.append({
            "Datetime": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
            "Open":     p - 0.1,
            "High":     p + 0.3,
            "Low":      p - 0.3,
            "Close":    p,
            "Volume":   1000.0,
        })
    return pd.DataFrame(rows)


# ── Tests ─────────────────────────────────────────────────────────────

class TestSwingDetector:

    def test_returns_dataframe(self):
        det = SwingDetector(window=2)
        df  = make_simple_df()
        result = det.run_on_df(df)
        assert isinstance(result, pd.DataFrame)

    def test_swing_high_low_columns_exist(self):
        det    = SwingDetector(window=2)
        df     = make_simple_df()
        result = det.run_on_df(df)
        assert "Swing_High" in result.columns
        assert "Swing_Low"  in result.columns

    def test_swing_strength_column_exists(self):
        det    = SwingDetector(window=2)
        df     = make_simple_df()
        result = det.run_on_df(df)
        assert "Swing_Strength" in result.columns

    def test_swing_strength_in_range(self):
        det    = SwingDetector(window=2)
        df     = make_simple_df(50)
        result = det.run_on_df(df)
        strengths = result.loc[result["Swing_High"] | result["Swing_Low"], "Swing_Strength"]
        assert (strengths >= 0).all()
        assert (strengths <= 100).all()

    def test_some_swings_detected(self):
        det    = SwingDetector(window=2)
        df     = make_simple_df(50)
        result = det.run_on_df(df)
        n_swings = (result["Swing_High"] | result["Swing_Low"]).sum()
        assert n_swings > 0, "Expected at least one swing in a 50-bar series"

    def test_swing_high_is_local_max(self):
        det    = SwingDetector(window=2)
        df     = make_simple_df(50)
        result = det.run_on_df(df)
        w = 2
        for i, row in result.iterrows():
            if row["Swing_High"] and w <= i <= len(result) - w - 1:
                window_highs = result["High"].iloc[i - w: i + w + 1]
                assert row["High"] == window_highs.max()

    def test_swing_low_is_local_min(self):
        det    = SwingDetector(window=2)
        df     = make_simple_df(50)
        result = det.run_on_df(df)
        w = 2
        for i, row in result.iterrows():
            if row["Swing_Low"] and w <= i <= len(result) - w - 1:
                window_lows = result["Low"].iloc[i - w: i + w + 1]
                assert row["Low"] == window_lows.min()

    def test_no_simultaneous_high_and_low(self):
        """A bar cannot be both a swing high and a swing low."""
        det    = SwingDetector(window=2)
        df     = make_simple_df(50)
        result = det.run_on_df(df)
        both   = result["Swing_High"] & result["Swing_Low"]
        assert both.sum() == 0

    def test_window_parameter_respected(self):
        """Larger window should detect fewer (more significant) swings."""
        df      = make_simple_df(80)
        det_w2  = SwingDetector(window=2)
        det_w5  = SwingDetector(window=5)
        res_w2  = det_w2.run_on_df(df)
        res_w5  = det_w5.run_on_df(df)
        n_w2    = (res_w2["Swing_High"] | res_w2["Swing_Low"]).sum()
        n_w5    = (res_w5["Swing_High"] | res_w5["Swing_Low"]).sum()
        assert n_w2 >= n_w5, "Smaller window should detect >= swings vs larger window"
