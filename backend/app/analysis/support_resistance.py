"""
support_resistance.py
=====================
SupportResistanceAnalyzer detects key price levels by clustering
swing highs and swing lows.

Question answered: Where are the key price levels?

Algorithm:
    1. Collect all swing highs (→ resistance candidates) and
       swing lows (→ support candidates) from the structure table.
    2. Cluster nearby levels within (cluster_tolerance × ATR).
    3. Score each cluster by:
           - touch count (how many swings fall in the cluster)
           - recency     (more recent = higher score)
           - strength    (average swing quality score)
    4. Filter by minimum_strength and maximum distance from price.

Output:
    Populates context.support_levels and context.resistance_levels
    with List[SupportResistanceLevel].
"""

from __future__ import annotations
from typing import List

import numpy as np
import pandas as pd

from backend.app.core.base_analyzer import BaseAnalyzer
from backend.app.core.analysis_context import AnalysisContext
from backend.app.core.models import SupportResistanceLevel
from backend.app.core.constants import SUPPORT, RESISTANCE


class SupportResistanceAnalyzer(BaseAnalyzer):
    """
    Cluster-based support and resistance detector.

    Args:
        cluster_tolerance : ATR multiples within which levels are merged (default 0.5)
        max_levels        : Maximum levels to return per side (default 5)
        lookback          : Number of recent swing points to consider (default 50)
        min_strength      : Minimum cluster score to include (default 20)
    """

    name = "SupportResistanceAnalyzer"

    def __init__(
        self,
        cluster_tolerance: float = 0.5,
        max_levels:        int   = 5,
        lookback:          int   = 50,
        min_strength:      float = 20.0,
    ) -> None:
        self.cluster_tolerance = cluster_tolerance
        self.max_levels        = max_levels
        self.lookback          = lookback
        self.min_strength      = min_strength

    # ─────────────────────────────────────────────────────────────────
    def _compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Return the most recent ATR value."""
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"].shift(1)
        tr = pd.concat(
            [high - low, (high - close).abs(), (low - close).abs()], axis=1
        ).max(axis=1)
        atr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        return float(atr.iloc[-1]) if not atr.empty else 1.0

    # ─────────────────────────────────────────────────────────────────
    def _cluster_levels(
        self,
        prices: List[float],
        strengths: List[float],
        datetimes: List[str],
        tolerance: float,
    ) -> List[dict]:
        """
        Merge nearby price levels into clusters.

        Returns list of dicts with keys: price, touch_count, strength, last_tested.
        """
        if not prices:
            return []

        # Sort by price
        combined   = sorted(zip(prices, strengths, datetimes), key=lambda x: x[0])
        clusters: List[dict] = []

        for price, strength, dt in combined:
            merged = False
            for cluster in clusters:
                if abs(price - cluster["price"]) <= tolerance:
                    # Merge into cluster: update centroid
                    n = cluster["touch_count"]
                    cluster["price"]       = (cluster["price"] * n + price) / (n + 1)
                    cluster["strength"]    += strength
                    cluster["touch_count"] += 1
                    # Keep most recent datetime
                    if dt > cluster["last_tested"]:
                        cluster["last_tested"] = dt
                    merged = True
                    break
            if not merged:
                clusters.append(
                    {
                        "price":       price,
                        "strength":    strength,
                        "touch_count": 1,
                        "last_tested": dt,
                    }
                )

        # Normalise strength to 0–100
        max_s = max(c["strength"] for c in clusters) if clusters else 1
        for c in clusters:
            c["strength"] = round(c["strength"] / max_s * 100, 1)

        return clusters

    # ─────────────────────────────────────────────────────────────────
    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        """
        Populate context.support_levels and context.resistance_levels.
        """
        df            = context.ohlc
        structure_df  = context.structure

        if df is None or structure_df is None or structure_df.empty:
            return context

        atr       = self._compute_atr(df)
        tolerance = self.cluster_tolerance * atr

        current_price = float(df["Close"].iloc[-1])

        # ── Collect swing highs → resistance candidates ──────────
        highs = structure_df[
            (structure_df["Swing_Type"] == "High") &
            (structure_df["Price"] > current_price)
        ].tail(self.lookback)

        # ── Collect swing lows → support candidates ───────────────
        lows = structure_df[
            (structure_df["Swing_Type"] == "Low") &
            (structure_df["Price"] < current_price)
        ].tail(self.lookback)

        # ── Convert datetime to string for comparison ─────────────
        def _to_str(col):
            return col.astype(str).tolist()

        # ── Cluster resistance levels ─────────────────────────────
        res_clusters = self._cluster_levels(
            prices    = highs["Price"].tolist(),
            strengths = highs.get("Swing_Strength", pd.Series([50] * len(highs))).tolist(),
            datetimes = _to_str(highs["Datetime"]),
            tolerance = tolerance,
        )
        res_clusters.sort(key=lambda x: -x["strength"])

        context.resistance_levels = [
            SupportResistanceLevel(
                level_type   = RESISTANCE,
                price        = round(c["price"], 4),
                strength     = c["strength"],
                touch_count  = c["touch_count"],
                last_tested  = c["last_tested"],
                distance_pct = round(abs(c["price"] - current_price) / current_price * 100, 2),
            )
            for c in res_clusters
            if c["strength"] >= self.min_strength
        ][: self.max_levels]

        # ── Cluster support levels ────────────────────────────────
        sup_clusters = self._cluster_levels(
            prices    = lows["Price"].tolist(),
            strengths = lows.get("Swing_Strength", pd.Series([50] * len(lows))).tolist(),
            datetimes = _to_str(lows["Datetime"]),
            tolerance = tolerance,
        )
        sup_clusters.sort(key=lambda x: -x["strength"])

        context.support_levels = [
            SupportResistanceLevel(
                level_type   = SUPPORT,
                price        = round(c["price"], 4),
                strength     = c["strength"],
                touch_count  = c["touch_count"],
                last_tested  = c["last_tested"],
                distance_pct = round(abs(c["price"] - current_price) / current_price * 100, 2),
            )
            for c in sup_clusters
            if c["strength"] >= self.min_strength
        ][: self.max_levels]

        return context

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: AnalysisContext) -> None:
        print(f"\n── {self.name} ──────────────────────────")
        print(f"  Resistance levels : {len(context.resistance_levels)}")
        for r in context.resistance_levels:
            print(f"    {r.price:.4f}  strength={r.strength:.0f}  touches={r.touch_count}  dist={r.distance_pct:.2f}%")
        print(f"  Support levels    : {len(context.support_levels)}")
        for s in context.support_levels:
            print(f"    {s.price:.4f}  strength={s.strength:.0f}  touches={s.touch_count}  dist={s.distance_pct:.2f}%")
