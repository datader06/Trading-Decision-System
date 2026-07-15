"""
supply_demand.py
================
SupplyDemandAnalyzer detects institutional supply and demand zones
using objective, rule-based criteria.

Question answered: Where are the institutional buying and selling areas?

Detection logic:
    Supply Zone (origin of a bearish impulse):
        1. Find a strong bearish candle (body ≥ 1.5 × ATR).
        2. Confirm the move: next N bars move ≥ 2 × zone height downward.
        3. Zone top  = candle high, zone bottom = candle open (or close if open < close).

    Demand Zone (origin of a bullish impulse):
        1. Find a strong bullish candle (body ≥ 1.5 × ATR).
        2. Confirm the move: next N bars move ≥ 2 × zone height upward.
        3. Zone bottom = candle low, zone top = candle open (or close if open > close).

Scoring per zone:
    strength_score   : impulse magnitude / ATR (capped at 100)
    freshness_score  : 100 if never re-entered, decreases with retests
    retest_count     : number of times price re-entered the zone
"""

from __future__ import annotations
from typing import List

import numpy as np
import pandas as pd

from backend.app.core.base_analyzer import BaseAnalyzer
from backend.app.core.analysis_context import AnalysisContext
from backend.app.core.models import Zone
from backend.app.core.constants import (
    SUPPLY_ZONE, DEMAND_ZONE,
    FRESH, TESTED, VIOLATED,
)


class SupplyDemandAnalyzer(BaseAnalyzer):
    """
    Objective supply and demand zone detector.

    Args:
        atr_period        : ATR period (default 14)
        body_atr_mult     : Minimum candle body as multiple of ATR (default 1.5)
        move_zone_mult    : Minimum subsequent move as multiple of zone height (default 2.0)
        confirm_bars      : Number of bars to look ahead for move confirmation (default 10)
        max_zones         : Maximum number of zones to return per side (default 6)
    """

    name = "SupplyDemandAnalyzer"

    def __init__(
        self,
        atr_period:    int   = 14,
        body_atr_mult: float = 1.5,
        move_zone_mult: float = 2.0,
        confirm_bars:  int   = 10,
        max_zones:     int   = 6,
    ) -> None:
        self.atr_period     = atr_period
        self.body_atr_mult  = body_atr_mult
        self.move_zone_mult = move_zone_mult
        self.confirm_bars   = confirm_bars
        self.max_zones      = max_zones

    # ─────────────────────────────────────────────────────────────────
    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"].shift(1)
        tr    = pd.concat(
            [high - low, (high - close).abs(), (low - close).abs()], axis=1
        ).max(axis=1)
        return tr.ewm(alpha=1 / self.atr_period, min_periods=self.atr_period, adjust=False).mean()

    # ─────────────────────────────────────────────────────────────────
    def _count_retests(self, df: pd.DataFrame, zone: Zone, created_idx: int) -> int:
        """Count how many times price re-entered a zone after it was created."""
        count = 0
        for i in range(created_idx + 1, len(df)):
            low_i  = df["Low"].iloc[i]
            high_i = df["High"].iloc[i]
            if low_i <= zone.top and high_i >= zone.bottom:
                count += 1
        return count

    # ─────────────────────────────────────────────────────────────────
    def _freshness(self, retest_count: int) -> tuple[str, float]:
        """Return freshness label and score based on retest count."""
        if retest_count == 0:
            return FRESH, 100.0
        elif retest_count <= 2:
            return TESTED, max(40.0, 100.0 - retest_count * 30)
        else:
            return VIOLATED, 10.0

    # ─────────────────────────────────────────────────────────────────
    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        """
        Detect supply and demand zones and populate the context.
        """
        df = context.ohlc
        if df is None or len(df) < self.atr_period + self.confirm_bars:
            return context

        # Ensure a clean integer index copy
        df = df.reset_index(drop=False) if df.index.name == "Datetime" else df.copy()
        atr = self._compute_atr(df)

        supply_zones: List[Zone] = []
        demand_zones: List[Zone] = []

        # Determine datetime column
        dt_col = "Datetime" if "Datetime" in df.columns else df.index.name or "index"

        for i in range(self.atr_period, len(df) - self.confirm_bars):
            row     = df.iloc[i]
            atr_val = atr.iloc[i]
            if np.isnan(atr_val) or atr_val == 0:
                continue

            body   = abs(row["Close"] - row["Open"])
            c_high = row["High"]
            c_low  = row["Low"]
            c_open = row["Open"]
            c_close= row["Close"]

            # ── Demand Zone (bullish impulse candle) ──────────────
            if c_close > c_open and body >= self.body_atr_mult * atr_val:
                zone_bottom = c_low
                zone_top    = c_open   # base candle body bottom
                zone_height = zone_top - zone_bottom if zone_top > zone_bottom else atr_val

                # Confirm: price moves up ≥ move_zone_mult × zone height
                future   = df.iloc[i + 1: i + 1 + self.confirm_bars]
                max_high = future["High"].max()
                if max_high - zone_top >= self.move_zone_mult * zone_height:
                    retests          = self._count_retests(df, Zone(
                        zone_type       = DEMAND_ZONE,
                        top             = zone_top,
                        bottom          = zone_bottom,
                        time_created    = str(row.get(dt_col, i)),
                        freshness       = FRESH,
                        strength_score  = 0,
                        freshness_score = 0,
                    ), i)
                    freshness_label, freshness_score = self._freshness(retests)
                    strength_score = round(
                        min((max_high - zone_top) / atr_val / 3.0, 1.0) * 100, 1
                    )
                    demand_zones.append(Zone(
                        zone_type       = DEMAND_ZONE,
                        top             = round(zone_top, 4),
                        bottom          = round(zone_bottom, 4),
                        time_created    = str(row.get(dt_col, i)),
                        freshness       = freshness_label,
                        strength_score  = strength_score,
                        freshness_score = freshness_score,
                        retest_count    = retests,
                    ))

            # ── Supply Zone (bearish impulse candle) ──────────────
            elif c_close < c_open and body >= self.body_atr_mult * atr_val:
                zone_top    = c_high
                zone_bottom = c_open   # base candle body top
                zone_height = zone_top - zone_bottom if zone_top > zone_bottom else atr_val

                # Confirm: price moves down ≥ move_zone_mult × zone height
                future   = df.iloc[i + 1: i + 1 + self.confirm_bars]
                min_low  = future["Low"].min()
                if zone_bottom - min_low >= self.move_zone_mult * zone_height:
                    retests          = self._count_retests(df, Zone(
                        zone_type       = SUPPLY_ZONE,
                        top             = zone_top,
                        bottom          = zone_bottom,
                        time_created    = str(row.get(dt_col, i)),
                        freshness       = FRESH,
                        strength_score  = 0,
                        freshness_score = 0,
                    ), i)
                    freshness_label, freshness_score = self._freshness(retests)
                    strength_score = round(
                        min((zone_bottom - min_low) / atr_val / 3.0, 1.0) * 100, 1
                    )
                    supply_zones.append(Zone(
                        zone_type       = SUPPLY_ZONE,
                        top             = round(zone_top, 4),
                        bottom          = round(zone_bottom, 4),
                        time_created    = str(row.get(dt_col, i)),
                        freshness       = freshness_label,
                        strength_score  = strength_score,
                        freshness_score = freshness_score,
                        retest_count    = retests,
                    ))

        # Sort by strength + freshness combined score and keep top N
        def _zone_rank(z: Zone) -> float:
            return z.strength_score * 0.6 + z.freshness_score * 0.4

        context.supply_zones = sorted(supply_zones, key=_zone_rank, reverse=True)[: self.max_zones]
        context.demand_zones = sorted(demand_zones, key=_zone_rank, reverse=True)[: self.max_zones]

        return context

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: AnalysisContext) -> None:
        print(f"\n── {self.name} ───────────────────────────")
        print(f"  Supply zones  : {len(context.supply_zones)}")
        for z in context.supply_zones:
            print(f"    {z.bottom:.4f}–{z.top:.4f}  str={z.strength_score:.0f}  fresh={z.freshness}  retests={z.retest_count}")
        print(f"  Demand zones  : {len(context.demand_zones)}")
        for z in context.demand_zones:
            print(f"    {z.bottom:.4f}–{z.top:.4f}  str={z.strength_score:.0f}  fresh={z.freshness}  retests={z.retest_count}")
