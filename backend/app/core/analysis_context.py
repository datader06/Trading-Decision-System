"""
analysis_context.py
===================
AnalysisContext is the single shared object that carries every
intermediate result produced by the Analysis Engine pipeline.

Think of it as a "blackboard": each analyzer writes its results
here and the next analyzer reads from it.

Design principles:
    - One object, no circular dependencies.
    - Every field is typed and documented.
    - The `ai_annotations` dict is reserved for future ML model outputs.
    - `reset()` returns a clean instance for a new analysis run.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List

import pandas as pd

from backend.app.core.models import (
    TrendResult,
    SupportResistanceLevel,
    Zone,
    MomentumState,
    VolatilityState,
    MTFAlignment,
    ConfluenceScore,
    TradePlan,
    TradeSignal,
)


@dataclass
class AnalysisContext:
    """
    Central data carrier for the full analysis pipeline.

    Populated sequentially as each module runs.
    Passed into and returned from every BaseAnalyzer.analyze() call.
    """

    # ── Inputs ────────────────────────────────────────────────────────
    ticker:   str = ""
    interval: str = ""     # Primary download interval (e.g. "5m")

    # ── Raw OHLCV data ────────────────────────────────────────────────
    # Keyed by timeframe resample string (e.g. "1h", "4h", "1D")
    ohlc_by_timeframe: Dict[str, pd.DataFrame] = field(default_factory=dict)

    # Primary working timeframe OHLC (set during pipeline init)
    ohlc: Optional[pd.DataFrame] = None

    # ── Market Structure (per timeframe) ──────────────────────────────
    # Each value is a tuple: (ohlc_with_swings_df, structure_df)
    structure_by_timeframe: Dict[str, tuple] = field(default_factory=dict)

    # Primary timeframe structure
    swings:    Optional[pd.DataFrame] = None   # Full OHLC with Swing_High/Low columns
    structure: Optional[pd.DataFrame] = None   # Swing point table

    # ── Trend (per timeframe) ─────────────────────────────────────────
    trend_by_timeframe: Dict[str, TrendResult] = field(default_factory=dict)

    # Primary timeframe trend
    trend: Optional[TrendResult] = None

    # ── Support & Resistance ──────────────────────────────────────────
    support_levels:    List[SupportResistanceLevel] = field(default_factory=list)
    resistance_levels: List[SupportResistanceLevel] = field(default_factory=list)

    # ── Supply & Demand Zones ─────────────────────────────────────────
    supply_zones: List[Zone] = field(default_factory=list)
    demand_zones: List[Zone] = field(default_factory=list)

    # ── Momentum ──────────────────────────────────────────────────────
    momentum: Optional[MomentumState] = None

    # ── Volatility ────────────────────────────────────────────────────
    volatility: Optional[VolatilityState] = None

    # ── Multi-Timeframe Alignment ──────────────────────────────────────
    mtf_alignment: Optional[MTFAlignment] = None

    # ── Decision Layer ────────────────────────────────────────────────
    confluence:  Optional[ConfluenceScore] = None
    trade_plan:  Optional[TradePlan]       = None
    signal:      Optional[TradeSignal]     = None

    # ── AI Extension Point ────────────────────────────────────────────
    ai_annotations: Dict[str, object] = field(default_factory=dict)

    # ─────────────────────────────────────────────────────────────────
    def reset(self) -> "AnalysisContext":
        """Return a fresh context, preserving ticker and interval."""
        return AnalysisContext(ticker=self.ticker, interval=self.interval)

    # ─────────────────────────────────────────────────────────────────
    def summary(self) -> None:
        """Print a high-level pipeline status summary."""
        print(f"\n{'═'*55}")
        print(f"  Analysis Context — {self.ticker}")
        print(f"{'═'*55}")

        def _status(val) -> str:
            return "✓" if val is not None else "✗"

        tf_loaded = len(self.ohlc_by_timeframe)

        print(f"  Timeframes loaded    : {tf_loaded}")
        print(f"  Swings detected      : {_status(self.swings)}")
        print(f"  Structure built      : {_status(self.structure)}")
        print(f"  Trend analysed       : {_status(self.trend)}")
        print(f"  S/R levels           : {len(self.support_levels)} support, {len(self.resistance_levels)} resistance")
        print(f"  Supply/Demand zones  : {len(self.supply_zones)} supply, {len(self.demand_zones)} demand")
        print(f"  Momentum             : {_status(self.momentum)}")
        print(f"  Volatility           : {_status(self.volatility)}")
        print(f"  MTF Alignment        : {_status(self.mtf_alignment)}")
        print(f"  Confluence Score     : {self.confluence.total:.1f}/100" if self.confluence else "  Confluence Score     : ✗")
        print(f"  Signal               : {_status(self.signal)}")

        if self.trend:
            print(f"\n  Trend   : {self.trend.direction} ({self.trend.confidence}) — strength {self.trend.strength:.1f}/100")

        if self.momentum:
            print(f"  Momentum: {self.momentum.direction} — score {self.momentum.score:.1f}/100")

        if self.volatility:
            print(f"  Volatility: {self.volatility.regime} — ATR {self.volatility.atr:.4f}")

        if self.mtf_alignment:
            print(f"  MTF Tag : {self.mtf_alignment.tag} — score {self.mtf_alignment.score:.1f}/100")

        if self.signal:
            action = "✅ TAKE TRADE" if self.signal.take_trade else "❌ SKIP"
            print(f"\n  Signal  : {action}")
            print(f"  Direction : {self.signal.direction}")
            print(f"  Confidence: {self.signal.confidence:.1f}%")
            print(f"  R:R       : {self.signal.risk_reward:.2f}")

        print(f"{'═'*55}\n")
