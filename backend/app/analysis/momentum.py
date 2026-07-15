"""
momentum.py
===========
MomentumAnalyzer computes a composite momentum state from multiple
technical indicators.

Question answered: What is the current momentum state?

Indicators:
    RSI(14)    — overbought / oversold / neutral
    MACD       — histogram direction and signal cross
    ADX(14)    — trend strength (>25 = trending)
    ROC(10)    — rate of change (short-term momentum)
    EMA Slope  — direction and angle of EMA20

Composite Score (0–100):
    RSI contribution    : 25 pts
    MACD contribution   : 25 pts
    ADX contribution    : 20 pts
    ROC contribution    : 15 pts
    EMA Slope           : 15 pts

Output:
    Populates context.momentum with a MomentumState.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.app.core.base_analyzer import BaseAnalyzer
from backend.app.core.analysis_context import AnalysisContext
from backend.app.core.models import MomentumState
from backend.app.core.constants import (
    BULLISH, BEARISH, NEUTRAL,
    MOMENTUM_BULLISH, MOMENTUM_BEARISH, MOMENTUM_NEUTRAL,
    OVERBOUGHT, OVERSOLD,
)


class MomentumAnalyzer(BaseAnalyzer):
    """
    Composite momentum engine.

    Args:
        rsi_period   : RSI period (default 14)
        atr_period   : ATR period (default 14)
        roc_period   : Rate of Change period (default 10)
        adx_period   : ADX period (default 14)
    """

    name = "MomentumAnalyzer"

    def __init__(
        self,
        rsi_period: int = 14,
        roc_period: int = 10,
        adx_period: int = 14,
    ) -> None:
        self.rsi_period = rsi_period
        self.roc_period = roc_period
        self.adx_period = adx_period

    # ── Indicator helpers ─────────────────────────────────────────────

    def _rsi(self, close: pd.Series) -> float:
        delta = close.diff()
        gain  = delta.clip(lower=0).ewm(com=self.rsi_period - 1, adjust=False).mean()
        loss  = (-delta.clip(upper=0)).ewm(com=self.rsi_period - 1, adjust=False).mean()
        # Avoid division by zero: when all moves are gains, RSI → 100; all losses → 0
        with np.errstate(divide="ignore", invalid="ignore"):
            rs  = np.where(loss == 0, np.inf, gain / loss)
        rs_s  = pd.Series(rs, index=close.index)
        rsi   = 100 - (100 / (1 + rs_s))
        val   = float(rsi.iloc[-1])
        return val if not np.isnan(val) else 50.0

    def _macd(self, close: pd.Series) -> tuple[float, float]:
        """Return (macd_line, histogram)."""
        fast     = close.ewm(span=12, adjust=False).mean()
        slow     = close.ewm(span=26, adjust=False).mean()
        macd     = fast - slow
        signal   = macd.ewm(span=9, adjust=False).mean()
        hist     = macd - signal
        return float(macd.iloc[-1]), float(hist.iloc[-1])

    def _adx(self, df: pd.DataFrame) -> float:
        """Compute ADX using Wilder's smoothing."""
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"]
        p     = self.adx_period

        up_move   = high.diff()
        down_move = -low.diff()
        plus_dm   = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm  = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        tr = pd.concat(
            [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
        ).max(axis=1)

        atr      = tr.ewm(alpha=1 / p, min_periods=p, adjust=False).mean()
        plus_di  = 100 * plus_dm.ewm(alpha=1 / p, min_periods=p, adjust=False).mean() / atr
        minus_di = 100 * minus_dm.ewm(alpha=1 / p, min_periods=p, adjust=False).mean() / atr
        dx       = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
        adx      = dx.ewm(alpha=1 / p, min_periods=p, adjust=False).mean()
        return float(adx.iloc[-1]) if not adx.empty else 20.0

    def _roc(self, close: pd.Series) -> float:
        roc = close.pct_change(self.roc_period) * 100
        return float(roc.iloc[-1]) if not roc.empty else 0.0

    def _ema_slope(self, close: pd.Series, period: int = 20) -> float:
        """Return slope of EMA (today − 5 bars ago, normalised by price)."""
        ema = close.ewm(span=period, adjust=False).mean()
        if len(ema) < 6:
            return 0.0
        slope = (ema.iloc[-1] - ema.iloc[-6]) / ema.iloc[-6] * 100
        return float(slope)

    # ─────────────────────────────────────────────────────────────────
    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        df = context.ohlc
        if df is None or len(df) < 30:
            return context

        close = df["Close"]

        # ── Compute indicators ────────────────────────────────────
        rsi_val              = self._rsi(close)
        macd_line, macd_hist = self._macd(close)
        adx_val              = self._adx(df)
        roc_val              = self._roc(close)
        slope                = self._ema_slope(close)

        # ── RSI score (0–25) ──────────────────────────────────────
        if rsi_val >= 70:
            rsi_state = OVERBOUGHT
            rsi_score = 25.0   # strong bearish
            rsi_dir   = BEARISH
        elif rsi_val <= 30:
            rsi_state = OVERSOLD
            rsi_score = 25.0   # strong bullish
            rsi_dir   = BULLISH
        elif rsi_val > 55:
            rsi_state = "Neutral"
            rsi_score = round((rsi_val - 50) / 50 * 25, 1)
            rsi_dir   = BULLISH
        elif rsi_val < 45:
            rsi_state = "Neutral"
            rsi_score = round((50 - rsi_val) / 50 * 25, 1)
            rsi_dir   = BEARISH
        else:
            rsi_state = "Neutral"
            rsi_score = 0.0
            rsi_dir   = NEUTRAL

        # ── MACD score (0–25) ─────────────────────────────────────
        macd_score = min(abs(macd_hist) / (close.iloc[-1] * 0.001 + 1e-9) * 25, 25.0)
        macd_dir   = BULLISH if macd_hist > 0 else BEARISH if macd_hist < 0 else NEUTRAL
        macd_signal_str = "Bullish" if macd_hist > 0 else "Bearish"

        # ── ADX score (0–20) ──────────────────────────────────────
        is_trending = adx_val > 25
        adx_score   = round(min(adx_val / 50.0, 1.0) * 20, 1)

        # ── ROC score (0–15) ─────────────────────────────────────
        roc_score = round(min(abs(roc_val) / 5.0, 1.0) * 15, 1)
        roc_dir   = BULLISH if roc_val > 0 else BEARISH if roc_val < 0 else NEUTRAL

        # ── EMA Slope score (0–15) ────────────────────────────────
        slope_score = round(min(abs(slope) / 2.0, 1.0) * 15, 1)
        slope_dir   = BULLISH if slope > 0 else BEARISH if slope < 0 else NEUTRAL

        # ── Composite score ───────────────────────────────────────
        total_score = rsi_score + macd_score + adx_score + roc_score + slope_score
        total_score = round(min(total_score, 100.0), 1)

        # ── Direction voting ──────────────────────────────────────
        votes = [rsi_dir, macd_dir, roc_dir, slope_dir]
        bull  = votes.count(BULLISH)
        bear  = votes.count(BEARISH)

        if bull > bear:
            direction = MOMENTUM_BULLISH
        elif bear > bull:
            direction = MOMENTUM_BEARISH
        else:
            direction = MOMENTUM_NEUTRAL

        context.momentum = MomentumState(
            score          = total_score,
            direction      = direction,
            rsi            = round(rsi_val, 2),
            rsi_state      = rsi_state,
            macd_histogram = round(macd_hist, 6),
            macd_signal    = macd_signal_str,
            adx            = round(adx_val, 2),
            is_trending    = is_trending,
            roc            = round(roc_val, 4),
            is_diverging   = False,   # divergence detection — future enhancement
        )

        return context

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: AnalysisContext) -> None:
        m = context.momentum
        if m is None:
            print("  MomentumAnalyzer: no result.")
            return
        print(f"\n── {self.name} ────────────────────────────")
        print(f"  Score     : {m.score:.1f} / 100")
        print(f"  Direction : {m.direction}")
        print(f"  RSI       : {m.rsi:.1f}  ({m.rsi_state})")
        print(f"  MACD Hist : {m.macd_histogram:.6f}  ({m.macd_signal})")
        print(f"  ADX       : {m.adx:.1f}  ({'Trending' if m.is_trending else 'Ranging'})")
        print(f"  ROC       : {m.roc:.4f}%")
