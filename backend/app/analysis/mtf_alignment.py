"""
mtf_alignment.py
================
MTFAlignmentAnalyzer runs the TrendEngine independently on each
available timeframe and produces a weighted alignment score.

Question answered: Do all timeframes agree on direction?

Weighting (matches Timeframe.weight):
    Daily  (D1)  : 40%
    4-Hour (H4)  : 25%
    1-Hour (H1)  : 20%
    15-Min (M15) : 10%
    5-Min  (M5)  :  5%

Scoring:
    Each timeframe votes +1 (Bullish), -1 (Bearish), or 0 (Neutral).
    Weighted sum is normalised to a 0–100 scale.

Tag thresholds:
    score ≥ 75  → Strong Bullish
    score ≥ 55  → Weak Bullish
    score ≤ 25  → Strong Bearish
    score ≤ 45  → Weak Bearish
    otherwise   → Mixed

Output:
    Populates context.mtf_alignment with an MTFAlignment.
    Also updates the `htf_trend` field on context.trend and context.ohlc
    market state for downstream use.
"""

from __future__ import annotations
from typing import Dict

import pandas as pd

from backend.app.core.base_analyzer import BaseAnalyzer
from backend.app.core.analysis_context import AnalysisContext
from backend.app.core.models import MTFAlignment
from backend.app.core.constants import (
    BULLISH, BEARISH, NEUTRAL,
    STRONG_BULL, WEAK_BULL, MIXED, WEAK_BEAR, STRONG_BEAR,
)
from backend.app.core.timeframe import Timeframe
from backend.app.market_structure.structure import MarketStructure
from backend.app.market_structure.swings import SwingDetector
from backend.app.market_structure.trend import TrendEngine


class MTFAlignmentAnalyzer(BaseAnalyzer):
    """
    Runs trend analysis on every available timeframe and computes
    a weighted directional alignment score.
    """

    name = "MTFAlignmentAnalyzer"

    # ─────────────────────────────────────────────────────────────────
    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        if not context.ohlc_by_timeframe:
            return context

        per_tf_trend: Dict[str, str] = {}
        weighted_score: float = 0.0
        total_weight:   float = 0.0

        for tf in Timeframe.ordered():
            tf_str = tf.resample_str
            if tf_str not in context.ohlc_by_timeframe:
                continue

            tf_df = context.ohlc_by_timeframe[tf_str].copy()
            if len(tf_df) < 30:
                continue

            # Reset index so Datetime is a column (structure expects this)
            if tf_df.index.name == "Datetime":
                tf_df = tf_df.reset_index()
            elif "Datetime" not in tf_df.columns:
                tf_df = tf_df.reset_index().rename(columns={"index": "Datetime"})

            # ── Detect swings ──────────────────────────────────────
            swing_det = SwingDetector(window=2)
            tf_swings = swing_det.run_on_df(tf_df)

            # ── Build structure table ─────────────────────────────
            structure_points = []
            last_high = last_low = None
            for idx, row in tf_swings.iterrows():
                if row["Swing_High"]:
                    if last_high is None:
                        s = "SH"
                    elif row["High"] > last_high:
                        s = "HH"
                    else:
                        s = "LH"
                    last_high = row["High"]
                    structure_points.append({
                        "Index": idx, "Datetime": row.get("Datetime", idx),
                        "Swing_Type": "High", "Price": row["High"],
                        "Structure": s,
                        "Swing_Strength": row.get("Swing_Strength", 50),
                    })
                elif row["Swing_Low"]:
                    if last_low is None:
                        s = "SL"
                    elif row["Low"] > last_low:
                        s = "HL"
                    else:
                        s = "LL"
                    last_low = row["Low"]
                    structure_points.append({
                        "Index": idx, "Datetime": row.get("Datetime", idx),
                        "Swing_Type": "Low", "Price": row["Low"],
                        "Structure": s,
                        "Swing_Strength": row.get("Swing_Strength", 50),
                    })

            if not structure_points:
                per_tf_trend[tf.display_name] = NEUTRAL
                continue

            structure_df = pd.DataFrame(structure_points)

            # ── Run TrendEngine ───────────────────────────────────
            trend_engine = TrendEngine(structure_df, tf_swings)
            trend_result, _ = trend_engine.run()

            direction = trend_result.direction
            per_tf_trend[tf.display_name] = direction
            context.trend_by_timeframe[tf_str] = trend_result

            # ── Weighted vote ─────────────────────────────────────
            vote = 1.0 if direction == BULLISH else (-1.0 if direction == BEARISH else 0.0)
            weighted_score += vote * tf.weight
            total_weight   += tf.weight

        # ── Normalise to 0–100 ────────────────────────────────────
        if total_weight > 0:
            # weighted_score ∈ [-1, +1]; map to [0, 100]
            normalised = (weighted_score / total_weight + 1) / 2 * 100
        else:
            normalised = 50.0

        normalised = round(normalised, 1)

        # ── Classify tag ──────────────────────────────────────────
        if normalised >= 75:
            tag = STRONG_BULL
            dominant = BULLISH
        elif normalised >= 55:
            tag = WEAK_BULL
            dominant = BULLISH
        elif normalised <= 25:
            tag = STRONG_BEAR
            dominant = BEARISH
        elif normalised <= 45:
            tag = WEAK_BEAR
            dominant = BEARISH
        else:
            tag = MIXED
            dominant = NEUTRAL

        context.mtf_alignment = MTFAlignment(
            score               = normalised,
            tag                 = tag,
            per_timeframe_trend = per_tf_trend,
            dominant_direction  = dominant,
        )

        return context

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: AnalysisContext) -> None:
        m = context.mtf_alignment
        if m is None:
            print("  MTFAlignmentAnalyzer: no result.")
            return
        print(f"\n── {self.name} ──────────────────────────")
        print(f"  Score     : {m.score:.1f} / 100")
        print(f"  Tag       : {m.tag}")
        print(f"  Dominant  : {m.dominant_direction}")
        print("  Per Timeframe:")
        for tf, direction in m.per_timeframe_trend.items():
            arrow = "↑" if direction == BULLISH else "↓" if direction == BEARISH else "→"
            print(f"    {tf:12s}  {arrow} {direction}")
