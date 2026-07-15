"""
market_state.py
===============
MarketState holds the running state of a single timeframe's market
as it is built up sequentially by the TrendEngine.

This is intentionally kept separate from TrendResult (which is the
final immutable snapshot) because MarketState is mutated bar-by-bar
during processing.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class MarketState:
    """
    Running state updated by the TrendEngine as it processes each swing point.
    """

    # ── Trend ─────────────────────────────────────────────────────────
    trend:            str   = "Neutral"
    trend_strength:   float = 0.0       # 0–100
    trend_confidence: str   = "Weak"    # Strong / Moderate / Weak

    # ── Latest Structure Levels ────────────────────────────────────────
    last_hh: Optional[float] = None
    last_hl: Optional[float] = None
    last_lh: Optional[float] = None
    last_ll: Optional[float] = None

    # ── Protected Levels (last valid HL in uptrend / LH in downtrend) ─
    protected_high: Optional[float] = None
    protected_low:  Optional[float] = None

    # ── Momentum / Volatility Context ─────────────────────────────────
    momentum_score:   float = 0.0
    volatility_state: str   = "Normal"   # Expanding / Normal / Compressing

    # ── Higher Timeframe Bias (set by MTFAlignmentAnalyzer) ───────────
    htf_trend:  str   = "Neutral"
    htf_weight: float = 0.0

    def __str__(self) -> str:
        lines = [
            "── Market State ───────────────────────────────",
            f"  Trend          : {self.trend} ({self.trend_confidence})",
            f"  Strength       : {self.trend_strength:.1f} / 100",
            f"  HTF Bias       : {self.htf_trend}",
            f"  Last HH        : {self.last_hh}",
            f"  Last HL        : {self.last_hl}",
            f"  Last LH        : {self.last_lh}",
            f"  Last LL        : {self.last_ll}",
            f"  Protected High : {self.protected_high}",
            f"  Protected Low  : {self.protected_low}",
            "──────────────────────────────────────────────",
        ]
        return "\n".join(lines)