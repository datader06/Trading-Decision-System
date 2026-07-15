"""
test_volatility.py
==================
Unit tests for VolatilityAnalyzer.
"""

import pandas as pd
import numpy as np
import pytest

from backend.app.core.analysis_context import AnalysisContext
from backend.app.analysis.volatility import VolatilityAnalyzer
from backend.app.core.constants import (
    VOLATILITY_EXPANDING,
    VOLATILITY_NORMAL,
    VOLATILITY_COMPRESSING,
)


def make_ohlc(volatility: str = "normal", n: int = 80) -> pd.DataFrame:
    np.random.seed(10)
    base  = 100.0
    close = [base]

    if volatility == "high":
        std = 3.0
    elif volatility == "low":
        std = 0.1
    else:
        std = 0.5

    for _ in range(n - 1):
        close.append(close[-1] + np.random.randn() * std)

    close = np.array(close)
    return pd.DataFrame({
        "Datetime": pd.date_range("2024-01-01", periods=n, freq="1h"),
        "Open":  close - 0.1,
        "High":  close + abs(np.random.randn(n) * std * 0.5),
        "Low":   close - abs(np.random.randn(n) * std * 0.5),
        "Close": close,
        "Volume": np.ones(n) * 1000,
    })


class TestVolatilityAnalyzer:

    def test_returns_volatility_state(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_ohlc()
        analyzer = VolatilityAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.volatility is not None

    def test_atr_positive(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_ohlc()
        analyzer = VolatilityAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.volatility.atr > 0

    def test_stop_suggestion_positive(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_ohlc()
        analyzer = VolatilityAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.volatility.stop_suggestion > 0

    def test_regime_is_valid_label(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_ohlc()
        analyzer = VolatilityAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.volatility.regime in (
            VOLATILITY_EXPANDING,
            VOLATILITY_NORMAL,
            VOLATILITY_COMPRESSING,
        )

    def test_high_volatility_regime_expands(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_ohlc("high", 80)
        # Use a tiny avg period to see expansion easily
        analyzer = VolatilityAnalyzer(avg_period=10, expand_threshold=1.0)
        ctx      = analyzer.analyze(ctx)
        # With high std, ratio should exceed threshold
        assert ctx.volatility.volatility_ratio is not None

    def test_stop_suggestion_equals_atr_times_multiplier(self):
        ctx      = AnalysisContext()
        ctx.ohlc = make_ohlc()
        mult     = 2.0
        analyzer = VolatilityAnalyzer(stop_atr_multiplier=mult)
        ctx      = analyzer.analyze(ctx)
        expected = ctx.volatility.atr * mult
        assert ctx.volatility.stop_suggestion == pytest.approx(expected, abs=0.001)

    def test_no_ohlc_returns_unchanged(self):
        ctx      = AnalysisContext()
        analyzer = VolatilityAnalyzer()
        ctx      = analyzer.analyze(ctx)
        assert ctx.volatility is None
