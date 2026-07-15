"""
trade_planner.py
================
TradePlanner constructs a concrete TradePlan from the analysis context.

Question answered: What exactly is the trade setup?

Entry logic:
    - Direction is determined by the dominant MTF trend and trend engine result.
    - Entry price = current close (market order) or zone midpoint (limit order).
    - Stop loss  = max(ATR stop, structure stop) — takes the worst case.
    - Target 1   = nearest opposing S/R or S&D zone.
    - Target 2   = 2× distance to Target 1.

The planner only generates a plan when confluence ≥ MIN_CONFLUENCE_SCORE.
"""

from __future__ import annotations
from typing import Optional

from backend.app.core.base_analyzer import BaseAnalyzer
from backend.app.core.analysis_context import AnalysisContext
from backend.app.core.models import TradePlan
from backend.app.core.constants import (
    BULLISH, BEARISH, NEUTRAL,
    LONG, SHORT, NO_TRADE,
    LIMIT_ORDER, MARKET_ORDER,
    MIN_CONFLUENCE_SCORE,
)


class TradePlanner(BaseAnalyzer):
    """
    Generates a structured TradePlan from an AnalysisContext.

    Args:
        target_rr : Desired R:R for Target 2 (default 2.0)
    """

    name = "TradePlanner"

    def __init__(self, target_rr: float = 2.0) -> None:
        self.target_rr = target_rr

    # ─────────────────────────────────────────────────────────────────
    def _determine_direction(self, context: AnalysisContext) -> str:
        """
        Use MTF alignment and primary trend to decide direction.
        Requires both to agree for a non-neutral direction.
        """
        mtf = context.mtf_alignment
        t   = context.trend

        if mtf is None or t is None:
            return NO_TRADE

        mtf_dir   = mtf.dominant_direction
        trend_dir = t.direction

        if mtf_dir == BULLISH and trend_dir == BULLISH:
            return LONG
        if mtf_dir == BEARISH and trend_dir == BEARISH:
            return SHORT
        return NO_TRADE

    # ─────────────────────────────────────────────────────────────────
    def _atr_stop(self, context: AnalysisContext, direction: str, entry: float) -> float:
        """Calculate stop using ATR suggestion from VolatilityAnalyzer."""
        v = context.volatility
        atr_dist = v.stop_suggestion if v else (entry * 0.01)
        if direction == LONG:
            return round(entry - atr_dist, 4)
        else:
            return round(entry + atr_dist, 4)

    # ─────────────────────────────────────────────────────────────────
    def _structure_stop(self, context: AnalysisContext, direction: str) -> Optional[float]:
        """
        Find the nearest structural stop level:
            Long  → last significant HL (protected low) or last support
            Short → last significant LH (protected high) or last resistance
        """
        t = context.trend
        if direction == LONG:
            level = t.protected_low if t else None
            if level is None and context.support_levels:
                level = context.support_levels[0].price
            return level
        else:
            level = t.protected_high if t else None
            if level is None and context.resistance_levels:
                level = context.resistance_levels[0].price
            return level

    # ─────────────────────────────────────────────────────────────────
    def _find_target(
        self,
        context: AnalysisContext,
        direction: str,
        entry: float,
        stop: float,
    ) -> tuple[float, float]:
        """
        Target 1 = nearest opposing zone / S/R level.
        Target 2 = entry ± (entry - stop) × target_rr.
        """
        risk = abs(entry - stop)
        price = entry

        if direction == LONG:
            # Look for nearest resistance or supply zone above entry
            candidates = (
                [r.price for r in context.resistance_levels if r.price > price]
                + [z.bottom for z in context.supply_zones if z.bottom > price]
            )
            t1 = min(candidates) if candidates else round(entry + risk * 1.5, 4)
        else:
            # Look for nearest support or demand zone below entry
            candidates = (
                [s.price for s in context.support_levels if s.price < price]
                + [z.top for z in context.demand_zones if z.top < price]
            )
            t1 = max(candidates) if candidates else round(entry - risk * 1.5, 4)

        t2 = (
            round(entry + risk * self.target_rr, 4)
            if direction == LONG
            else round(entry - risk * self.target_rr, 4)
        )

        return t1, t2

    # ─────────────────────────────────────────────────────────────────
    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        """
        Build a TradePlan if confluence is sufficient and direction is clear.
        """
        # Gate: require minimum confluence
        conf = context.confluence
        if conf is None or conf.total < MIN_CONFLUENCE_SCORE:
            return context

        direction = self._determine_direction(context)
        if direction == NO_TRADE:
            return context

        ohlc  = context.ohlc
        if ohlc is None:
            return context

        entry = round(float(ohlc["Close"].iloc[-1]), 4)

        # Stop Loss — worst case of ATR stop and structure stop
        atr_stop_price    = self._atr_stop(context, direction, entry)
        structure_stop    = self._structure_stop(context, direction)

        if structure_stop is not None:
            if direction == LONG:
                stop_loss = min(atr_stop_price, structure_stop)
            else:
                stop_loss = max(atr_stop_price, structure_stop)
        else:
            stop_loss = atr_stop_price

        stop_loss = round(stop_loss, 4)

        # Targets
        target_1, target_2 = self._find_target(context, direction, entry, stop_loss)

        # Build reasoning
        reasoning: list[str] = []
        t = context.trend
        m = context.mtf_alignment
        v = context.volatility

        if t:
            reasoning.append(
                f"Primary trend is {t.direction} (strength={t.strength:.0f}/100, {t.confidence})."
            )
        if m:
            reasoning.append(
                f"MTF alignment: {m.tag} (score={m.score:.0f}/100)."
            )
        for z in (context.demand_zones if direction == LONG else context.supply_zones):
            reasoning.append(
                f"{'Demand' if direction == LONG else 'Supply'} zone at "
                f"{z.bottom:.4f}–{z.top:.4f} ({z.freshness})."
            )
            break   # only mention the best zone
        if v:
            reasoning.append(f"Volatility regime: {v.regime} (ATR={v.atr:.4f}).")
        if conf:
            reasoning.append(f"Confluence score: {conf.total:.0f}/100.")

        context.trade_plan = TradePlan(
            direction            = direction,
            entry_type           = MARKET_ORDER,
            entry_price          = entry,
            stop_loss            = stop_loss,
            target_1             = round(target_1, 4),
            target_2             = round(target_2, 4),
            reasoning            = reasoning,
            confluence_score     = conf.total if conf else 0.0,
            confluence_breakdown = conf.breakdown if conf else {},
        )

        return context

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: AnalysisContext) -> None:
        p = context.trade_plan
        if p is None:
            print(f"  {self.name}: No trade plan generated.")
            return
        print(f"\n── Trade Plan ─────────────────────────────────")
        print(f"  Direction  : {p.direction}")
        print(f"  Entry Type : {p.entry_type}")
        print(f"  Entry      : {p.entry_price:.4f}")
        print(f"  Stop Loss  : {p.stop_loss:.4f}")
        print(f"  Target 1   : {p.target_1:.4f}")
        print(f"  Target 2   : {p.target_2:.4f}")
        print("  Reasoning:")
        for line in p.reasoning:
            print(f"    • {line}")
