"""
volatility.py
=============
VolatilityAnalyzer uses ATR to characterise the current volatility
regime and suggest appropriate stop distances.

Question answered: What is the current market volatility regime?

Calculations:
    ATR(14)          — current ATR value
    ATR SMA(50)      — average ATR over 50 bars
    Volatility ratio — ATR / ATR_SMA

Regime classification:
    ratio > 1.2  → Expanding   (market moving strongly, wider stops needed)
    ratio < 0.8  → Compressing (market coiling, breakout may be near)
    otherwise    → Normal

Output:
    Populates context.volatility with a VolatilityState.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.app.core.base_analyzer import BaseAnalyzer
from backend.app.core.analysis_context import AnalysisContext
from backend.app.core.models import VolatilityState
from backend.app.core.constants import (
    VOLATILITY_EXPANDING,
    VOLATILITY_NORMAL,
    VOLATILITY_COMPRESSING,
)


class VolatilityAnalyzer(BaseAnalyzer):
    """
    ATR-based volatility regime classifier.

    Args:
        atr_period         : ATR lookback period (default 14)
        avg_period         : Rolling average period for ATR SMA (default 50)
        stop_atr_multiplier: ATR multiplier for suggested stop distance (default 1.5)
        expand_threshold   : Ratio above which regime = Expanding (default 1.2)
        compress_threshold : Ratio below which regime = Compressing (default 0.8)
    """

    name = "VolatilityAnalyzer"

    def __init__(
        self,
        atr_period:          int   = 14,
        avg_period:          int   = 50,
        stop_atr_multiplier: float = 1.5,
        expand_threshold:    float = 1.2,
        compress_threshold:  float = 0.8,
    ) -> None:
        self.atr_period          = atr_period
        self.avg_period          = avg_period
        self.stop_atr_multiplier = stop_atr_multiplier
        self.expand_threshold    = expand_threshold
        self.compress_threshold  = compress_threshold

    # ─────────────────────────────────────────────────────────────────
    def _compute_atr_series(self, df: pd.DataFrame) -> pd.Series:
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"].shift(1)
        tr = pd.concat(
            [high - low, (high - close).abs(), (low - close).abs()], axis=1
        ).max(axis=1)
        return tr.ewm(alpha=1 / self.atr_period, min_periods=self.atr_period, adjust=False).mean()

    # ─────────────────────────────────────────────────────────────────
    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        df = context.ohlc
        if df is None or len(df) < self.atr_period + 5:
            return context

        atr_series = self._compute_atr_series(df)
        current_atr = float(atr_series.iloc[-1])

        # Average ATR over a longer window
        avg_atr = float(
            atr_series.rolling(self.avg_period).mean().iloc[-1]
            if len(atr_series) >= self.avg_period
            else atr_series.mean()
        )

        if np.isnan(avg_atr) or avg_atr == 0:
            avg_atr = current_atr if current_atr > 0 else 1.0

        ratio = current_atr / avg_atr

        # Classify regime
        if ratio >= self.expand_threshold:
            regime = VOLATILITY_EXPANDING
        elif ratio <= self.compress_threshold:
            regime = VOLATILITY_COMPRESSING
        else:
            regime = VOLATILITY_NORMAL

        stop_suggestion = round(current_atr * self.stop_atr_multiplier, 4)

        context.volatility = VolatilityState(
            atr              = round(current_atr, 4),
            atr_avg          = round(avg_atr, 4),
            volatility_ratio = round(ratio, 3),
            regime           = regime,
            stop_suggestion  = stop_suggestion,
        )

        return context

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: AnalysisContext) -> None:
        v = context.volatility
        if v is None:
            print("  VolatilityAnalyzer: no result.")
            return
        print(f"\n── {self.name} ─────────────────────────────")
        print(f"  ATR (current)   : {v.atr:.4f}")
        print(f"  ATR (average)   : {v.atr_avg:.4f}")
        print(f"  Volatility ratio: {v.volatility_ratio:.3f}")
        print(f"  Regime          : {v.regime}")
        print(f"  Suggested stop  : {v.stop_suggestion:.4f}")
