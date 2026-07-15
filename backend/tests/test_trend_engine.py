"""
test_trend_engine.py
====================
Unit tests for the enhanced TrendEngine.
"""

import pandas as pd
import numpy as np
import pytest

from backend.app.market_structure.trend import TrendEngine
from backend.app.core.models import TrendResult
from backend.app.core.constants import BULLISH, BEARISH, NEUTRAL, STRONG, MODERATE, WEAK


# ── Fixtures ──────────────────────────────────────────────────────────

def make_trending_data(direction: str = "up", n: int = 100) -> tuple:
    """Build a simple OHLCV df and matching structure_df."""
    np.random.seed(42)
    step = 1.0 if direction == "up" else -1.0
    prices = 100 + np.arange(n) * step + np.random.randn(n) * 0.2

    ohlc = pd.DataFrame({
        "Datetime": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "Open":     prices - 0.1,
        "High":     prices + 0.5,
        "Low":      prices - 0.5,
        "Close":    prices,
        "Volume":   np.random.randint(1000, 5000, n).astype(float),
    })

    # Build a minimal structure_df matching the direction
    if direction == "up":
        structure_data = [
            {"Index": 5,  "Datetime": ohlc["Datetime"].iloc[5],  "Swing_Type": "Low",  "Price": prices[5],  "Structure": "SL", "Swing_Strength": 60},
            {"Index": 15, "Datetime": ohlc["Datetime"].iloc[15], "Swing_Type": "High", "Price": prices[15], "Structure": "SH", "Swing_Strength": 65},
            {"Index": 25, "Datetime": ohlc["Datetime"].iloc[25], "Swing_Type": "Low",  "Price": prices[25], "Structure": "HL", "Swing_Strength": 70},
            {"Index": 35, "Datetime": ohlc["Datetime"].iloc[35], "Swing_Type": "High", "Price": prices[35], "Structure": "HH", "Swing_Strength": 75},
            {"Index": 45, "Datetime": ohlc["Datetime"].iloc[45], "Swing_Type": "Low",  "Price": prices[45], "Structure": "HL", "Swing_Strength": 70},
            {"Index": 55, "Datetime": ohlc["Datetime"].iloc[55], "Swing_Type": "High", "Price": prices[55], "Structure": "HH", "Swing_Strength": 80},
        ]
    else:
        structure_data = [
            {"Index": 5,  "Datetime": ohlc["Datetime"].iloc[5],  "Swing_Type": "High", "Price": prices[5],  "Structure": "SH", "Swing_Strength": 60},
            {"Index": 15, "Datetime": ohlc["Datetime"].iloc[15], "Swing_Type": "Low",  "Price": prices[15], "Structure": "SL", "Swing_Strength": 65},
            {"Index": 25, "Datetime": ohlc["Datetime"].iloc[25], "Swing_Type": "High", "Price": prices[25], "Structure": "LH", "Swing_Strength": 70},
            {"Index": 35, "Datetime": ohlc["Datetime"].iloc[35], "Swing_Type": "Low",  "Price": prices[35], "Structure": "LL", "Swing_Strength": 75},
            {"Index": 45, "Datetime": ohlc["Datetime"].iloc[45], "Swing_Type": "High", "Price": prices[45], "Structure": "LH", "Swing_Strength": 70},
            {"Index": 55, "Datetime": ohlc["Datetime"].iloc[55], "Swing_Type": "Low",  "Price": prices[55], "Structure": "LL", "Swing_Strength": 80},
        ]

    return ohlc, pd.DataFrame(structure_data)


# ── Tests ─────────────────────────────────────────────────────────────

class TestTrendEngine:

    def test_returns_trend_result(self):
        ohlc, structure = make_trending_data("up")
        engine = TrendEngine(structure, ohlc)
        result, state   = engine.run()
        assert isinstance(result, TrendResult)

    def test_bullish_trend_detected(self):
        ohlc, structure = make_trending_data("up")
        engine = TrendEngine(structure, ohlc)
        result, _       = engine.run()
        assert result.direction == BULLISH

    def test_bearish_trend_detected(self):
        ohlc, structure = make_trending_data("down")
        engine = TrendEngine(structure, ohlc)
        result, _       = engine.run()
        assert result.direction == BEARISH

    def test_strength_in_range(self):
        ohlc, structure = make_trending_data("up")
        engine = TrendEngine(structure, ohlc)
        result, _       = engine.run()
        assert 0.0 <= result.strength <= 100.0

    def test_component_scores_in_range(self):
        ohlc, structure = make_trending_data("up")
        engine = TrendEngine(structure, ohlc)
        result, _       = engine.run()
        assert 0 <= result.swing_score    <= 40
        assert 0 <= result.ma_score       <= 20
        assert 0 <= result.momentum_score <= 20
        assert 0 <= result.atr_score      <= 20

    def test_confidence_is_valid_label(self):
        ohlc, structure = make_trending_data("up")
        engine = TrendEngine(structure, ohlc)
        result, _       = engine.run()
        assert result.confidence in (STRONG, MODERATE, WEAK)

    def test_market_state_updated(self):
        ohlc, structure = make_trending_data("up")
        engine = TrendEngine(structure, ohlc)
        _, state        = engine.run()
        assert state.last_hh is not None
        assert state.last_hl is not None

    def test_empty_structure_df(self):
        ohlc, _ = make_trending_data("up")
        empty   = pd.DataFrame(columns=["Index", "Datetime", "Swing_Type", "Price", "Structure"])
        engine  = TrendEngine(empty, ohlc)
        result, _ = engine.run()
        # Should not raise, direction = Neutral
        assert result.direction == NEUTRAL
