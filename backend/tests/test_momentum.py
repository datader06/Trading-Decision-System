"""
test_momentum.py
================
Unit tests for MomentumAnalyzer.
"""

import pandas as pd
import numpy as np
import pytest

from backend.app.core.analysis_context import AnalysisContext
from backend.app.analysis.momentum import MomentumAnalyzer
from backend.app.core.constants import MOMENTUM_BULLISH, MOMENTUM_BEARISH, MOMENTUM_NEUTRAL


def make_bullish_ohlc(n: int = 80) -> pd.DataFrame:
    np.random.seed(1)
    prices = 100 + np.arange(n) * 0.5 + np.random.randn(n) * 0.1
    return pd.DataFrame({
        "Datetime": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "Open":  prices - 0.1,
        "High":  prices + 0.3,
        "Low":   prices - 0.3,
        "Close": prices,
        "Volume": np.ones(n) * 1000,
    })


def make_bearish_ohlc(n: int = 80) -> pd.DataFrame:
    np.random.seed(2)
    prices = 200 - np.arange(n) * 0.5 + np.random.randn(n) * 0.1
    return pd.DataFrame({
        "Datetime": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "Open":  prices + 0.1,
        "High":  prices + 0.3,
        "Low":   prices - 0.3,
        "Close": prices,
        "Volume": np.ones(n) * 1000,
    })


class TestMomentumAnalyzer:

    def test_returns_momentum_state(self):
        ctx     = AnalysisContext()
        ctx.ohlc = make_bullish_ohlc()
        analyzer = MomentumAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.momentum is not None

    def test_score_in_range(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_bullish_ohlc()
        analyzer = MomentumAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert 0 <= ctx.momentum.score <= 100

    def test_rsi_in_range(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_bullish_ohlc()
        analyzer = MomentumAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert 0 <= ctx.momentum.rsi <= 100

    def test_bullish_trend_yields_bullish_momentum(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_bullish_ohlc(100)
        analyzer = MomentumAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.momentum.direction == MOMENTUM_BULLISH

    def test_bearish_trend_yields_bearish_momentum(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_bearish_ohlc(100)
        analyzer = MomentumAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.momentum.direction == MOMENTUM_BEARISH

    def test_adx_not_negative(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_bullish_ohlc()
        analyzer = MomentumAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.momentum.adx >= 0

    def test_too_short_df_returns_none(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_bullish_ohlc(10)   # too short
        analyzer = MomentumAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.momentum is None

    def test_no_ohlc_returns_unchanged(self):
        ctx      = AnalysisContext()
        analyzer = MomentumAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.momentum is None
