"""
trend.py
========
Enhanced multi-factor TrendEngine.

Unlike the original (which only checked HH+HL existence), this engine
scores the trend across four independent dimensions and returns a rich
TrendResult object.

Scoring Components (total 100 pts):
    1. Swing Sequence Score  (0–40):  quality and consistency of HH/HL or LH/LL sequence
    2. MA Alignment Score    (0–20):  EMA20 > EMA50 > EMA200 (bull) or inverse (bear)
    3. Momentum Score        (0–20):  RSI position + MACD histogram direction
    4. ATR Expansion Score   (0–20):  current ATR vs rolling average (expanding = strong trend)

Confidence:
    ≥ 70  → Strong
    ≥ 45  → Moderate
    <  45  → Weak
"""

from __future__ import annotations
from typing import Optional

import numpy as np
import pandas as pd

from backend.app.core.constants import BULLISH, BEARISH, NEUTRAL, STRONG, MODERATE, WEAK
from backend.app.core.models import TrendResult
from backend.app.core.market_state import MarketState
from backend.app.market_structure.structure import MarketStructure


class TrendEngine:
    """
    Determines the market trend using a multi-factor scoring approach.

    Args:
        structure_df : Swing point table from MarketStructure.build()
        ohlc_df      : Full OHLCV DataFrame (datetime-indexed or with Datetime col)
        atr_period   : ATR period for volatility component
    """

    def __init__(
        self,
        structure_df: pd.DataFrame,
        ohlc_df: pd.DataFrame,
        atr_period: int = 14,
    ) -> None:
        self.structure_df = structure_df.copy()
        self.ohlc_df      = ohlc_df.copy()
        self.atr_period   = atr_period
        self.state        = MarketState()

    # ══════════════════════════════════════════════════════════════════
    # Internal Helpers
    # ══════════════════════════════════════════════════════════════════

    def _ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def _atr(self) -> pd.Series:
        df   = self.ohlc_df
        high = df["High"]
        low  = df["Low"]
        prev_close = df["Close"].shift(1)
        tr = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        return tr.ewm(alpha=1 / self.atr_period, min_periods=self.atr_period, adjust=False).mean()

    def _rsi(self, period: int = 14) -> pd.Series:
        close  = self.ohlc_df["Close"]
        delta  = close.diff()
        gain   = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
        loss   = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
        rs     = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def _macd_histogram(self) -> pd.Series:
        close  = self.ohlc_df["Close"]
        fast   = self._ema(close, 12)
        slow   = self._ema(close, 26)
        macd   = fast - slow
        signal = self._ema(macd, 9)
        return macd - signal

    # ══════════════════════════════════════════════════════════════════
    # Scoring Components
    # ══════════════════════════════════════════════════════════════════

    def _score_swing_sequence(self) -> tuple[float, str, MarketState]:
        """
        Score (0–40) based on the quality and consistency of the
        HH/HL (bullish) or LH/LL (bearish) swing sequence.

        Also updates and returns the running MarketState.
        """
        state = self.state
        df    = self.structure_df

        bull_points   = 0
        bear_points   = 0
        swing_quality = 0.0   # average swing strength from detector
        n_swings      = 0

        for _, row in df.iterrows():
            s = row["Structure"]
            p = row["Price"]
            q = float(row.get("Swing_Strength", 50))   # quality score 0–100

            if s == "HH":
                state.last_hh   = p
                bull_points    += 2
            elif s == "HL":
                state.last_hl   = p
                state.protected_low = p
                bull_points    += 2
            elif s == "LH":
                state.last_lh   = p
                state.protected_high = p
                bear_points    += 2
            elif s == "LL":
                state.last_ll   = p
                bear_points    += 2

            swing_quality += q
            n_swings      += 1

        avg_quality = (swing_quality / n_swings) if n_swings else 50.0

        # Direction
        if bull_points > bear_points:
            direction = BULLISH
            raw_score = bull_points
        elif bear_points > bull_points:
            direction = BEARISH
            raw_score = bear_points
        else:
            direction = NEUTRAL
            raw_score = 0

        # Normalise: assume max ~20 swing points → raw_score ∈ [0, 20]
        normalised = min(raw_score / 20.0, 1.0)
        # Weight by average swing quality
        quality_factor = avg_quality / 100.0
        score = round(normalised * quality_factor * 40, 1)

        return score, direction, state

    # ─────────────────────────────────────────────────────────────────
    def _score_ma_alignment(self) -> tuple[float, str]:
        """
        Score (0–20) based on EMA20 / EMA50 / EMA200 stack alignment.
        Full 20 pts when all three are perfectly aligned.
        """
        close  = self.ohlc_df["Close"]
        if len(close) < 200:
            return 10.0, NEUTRAL   # not enough data

        ema20  = self._ema(close, 20).iloc[-1]
        ema50  = self._ema(close, 50).iloc[-1]
        ema200 = self._ema(close, 200).iloc[-1]

        bull_count = sum([ema20 > ema50, ema50 > ema200, ema20 > ema200])
        bear_count = sum([ema20 < ema50, ema50 < ema200, ema20 < ema200])

        if bull_count >= 2:
            direction = BULLISH
            score = round((bull_count / 3) * 20, 1)
        elif bear_count >= 2:
            direction = BEARISH
            score = round((bear_count / 3) * 20, 1)
        else:
            direction = NEUTRAL
            score = 0.0

        return score, direction

    # ─────────────────────────────────────────────────────────────────
    def _score_momentum(self) -> tuple[float, str]:
        """
        Score (0–20) based on RSI position and MACD histogram direction.
        """
        rsi  = self._rsi()
        macd = self._macd_histogram()

        rsi_val  = rsi.iloc[-1]  if not rsi.empty  else 50.0
        macd_val = macd.iloc[-1] if not macd.empty else 0.0

        # RSI component (0–10)
        if rsi_val > 55:
            rsi_score = round(((rsi_val - 50) / 50) * 10, 1)
            rsi_dir   = BULLISH
        elif rsi_val < 45:
            rsi_score = round(((50 - rsi_val) / 50) * 10, 1)
            rsi_dir   = BEARISH
        else:
            rsi_score = 0.0
            rsi_dir   = NEUTRAL

        # MACD component (0–10)
        if macd_val > 0:
            macd_score = min(10.0, round(macd_val * 1000, 1))
            macd_dir   = BULLISH
        elif macd_val < 0:
            macd_score = min(10.0, round(abs(macd_val) * 1000, 1))
            macd_dir   = BEARISH
        else:
            macd_score = 0.0
            macd_dir   = NEUTRAL

        total_score = min(rsi_score + macd_score, 20.0)

        # Combine direction
        bull_votes = sum([rsi_dir == BULLISH, macd_dir == BULLISH])
        bear_votes = sum([rsi_dir == BEARISH, macd_dir == BEARISH])

        if bull_votes > bear_votes:
            direction = BULLISH
        elif bear_votes > bull_votes:
            direction = BEARISH
        else:
            direction = NEUTRAL

        return total_score, direction

    # ─────────────────────────────────────────────────────────────────
    def _score_atr_expansion(self) -> float:
        """
        Score (0–20) based on ATR expansion.
        Expanding ATR relative to its 50-bar mean signals a strong trend.
        """
        atr = self._atr()
        if len(atr.dropna()) < 50:
            return 10.0

        current = atr.iloc[-1]
        average = atr.rolling(50).mean().iloc[-1]

        if average == 0 or np.isnan(average):
            return 10.0

        ratio = current / average
        score = round(min(ratio / 2.0, 1.0) * 20, 1)   # ratio of 2× = max score
        return score

    # ══════════════════════════════════════════════════════════════════
    # Run
    # ══════════════════════════════════════════════════════════════════

    def run(self) -> tuple[TrendResult, MarketState]:
        """
        Run all scoring components and return a TrendResult.

        Returns:
            (TrendResult, MarketState)
        """
        swing_score,  swing_dir,   self.state = self._score_swing_sequence()
        ma_score,     ma_dir                  = self._score_ma_alignment()
        momentum_score, mom_dir               = self._score_momentum()
        atr_score                             = self._score_atr_expansion()

        total_strength = swing_score + ma_score + momentum_score + atr_score

        # ── Direction voting ──────────────────────────────────────
        votes = [swing_dir, ma_dir, mom_dir]
        bull_votes = votes.count(BULLISH)
        bear_votes = votes.count(BEARISH)

        if bull_votes >= 2:
            direction = BULLISH
        elif bear_votes >= 2:
            direction = BEARISH
        else:
            direction = NEUTRAL

        # ── Confidence tier ───────────────────────────────────────
        if total_strength >= 70:
            confidence = STRONG
        elif total_strength >= 45:
            confidence = MODERATE
        else:
            confidence = WEAK

        # ── Update state ──────────────────────────────────────────
        self.state.trend            = direction
        self.state.trend_strength   = total_strength
        self.state.trend_confidence = confidence

        result = TrendResult(
            direction      = direction,
            strength       = total_strength,
            confidence     = confidence,
            momentum_score = momentum_score,
            swing_score    = swing_score,
            ma_score       = ma_score,
            atr_score      = atr_score,
            last_hh        = self.state.last_hh,
            last_hl        = self.state.last_hl,
            last_lh        = self.state.last_lh,
            last_ll        = self.state.last_ll,
            protected_high = self.state.protected_high,
            protected_low  = self.state.protected_low,
        )

        return result, self.state

    def print_result(self, result: TrendResult) -> None:
        print("\n══════════════ TREND ENGINE ══════════════")
        print(f"  Direction      : {result.direction}")
        print(f"  Strength       : {result.strength:.1f} / 100")
        print(f"  Confidence     : {result.confidence}")
        print(f"  ── Component Scores ──────────────────")
        print(f"  Swing Sequence : {result.swing_score:.1f} / 40")
        print(f"  MA Alignment   : {result.ma_score:.1f}  / 20")
        print(f"  Momentum       : {result.momentum_score:.1f} / 20")
        print(f"  ATR Expansion  : {result.atr_score:.1f}  / 20")
        print(f"  ── Key Levels ────────────────────────")
        print(f"  Last HH  : {result.last_hh}   Last HL : {result.last_hl}")
        print(f"  Last LH  : {result.last_lh}   Last LL : {result.last_ll}")
        print("══════════════════════════════════════════\n")


# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    ms = MarketStructure("data/processed/RELIANCE_NS_1H.csv")
    ohlc_df, structure_df = ms.build()

    # Merge swing strength into structure_df if available
    engine = TrendEngine(structure_df, ohlc_df)
    result, state = engine.run()

    engine.print_result(result)
    print(state)