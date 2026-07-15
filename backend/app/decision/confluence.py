"""
confluence.py
=============
ConfluenceCalculator aggregates analysis results into a single
weighted score (0–100) representing the strength of a trade setup.

Question answered: How many independent confirmations exist?

Weights:
    Trend direction + strength     : 25%
    MTF alignment                  : 20%
    Supply/Demand zone proximity   : 20%
    Support/Resistance alignment   : 15%
    Momentum alignment             : 12%
    Volatility regime              :  8%

Only confluence scores ≥ MIN_CONFLUENCE_SCORE (default 60) will
be passed to the TradePlanner. Lower scores cause SignalEngine to
output NO_TRADE.
"""

from __future__ import annotations

from backend.app.core.base_analyzer import BaseAnalyzer
from backend.app.core.analysis_context import AnalysisContext
from backend.app.core.models import ConfluenceScore
from backend.app.core.constants import (
    BULLISH, BEARISH, NEUTRAL,
    MOMENTUM_BULLISH, MOMENTUM_BEARISH,
    VOLATILITY_NORMAL,
    MIN_CONFLUENCE_SCORE,
)


class ConfluenceCalculator(BaseAnalyzer):
    """
    Calculates a weighted confluence score from all analysis results.

    Weights are configurable via constructor to allow future ML override.
    """

    name = "ConfluenceCalculator"

    # Default factor weights (must sum to 1.0)
    DEFAULT_WEIGHTS = {
        "trend":      0.25,
        "mtf":        0.20,
        "zone":       0.20,
        "sr":         0.15,
        "momentum":   0.12,
        "volatility": 0.08,
    }

    def __init__(self, weights: dict | None = None) -> None:
        self.weights = weights or self.DEFAULT_WEIGHTS

    # ─────────────────────────────────────────────────────────────────
    def _score_trend(self, context: AnalysisContext) -> tuple[float, str]:
        """
        Score 0–100 based on trend strength and its alignment with
        the primary direction being evaluated.
        """
        t = context.trend
        if t is None:
            return 0.0, "No trend data"
        score = t.strength
        note  = f"Trend: {t.direction} ({t.confidence}, strength={t.strength:.0f})"
        return score, note

    # ─────────────────────────────────────────────────────────────────
    def _score_mtf(self, context: AnalysisContext) -> tuple[float, str]:
        m = context.mtf_alignment
        if m is None:
            return 0.0, "No MTF data"
        score = m.score
        note  = f"MTF: {m.tag} (score={m.score:.0f})"
        return score, note

    # ─────────────────────────────────────────────────────────────────
    def _score_zone(self, context: AnalysisContext) -> tuple[float, str]:
        """
        Score based on whether price is near a supply or demand zone.
        Prefers fresh zones, penalises violated zones.
        """
        ohlc = context.ohlc
        if ohlc is None:
            return 0.0, "No OHLC data"

        price      = float(ohlc["Close"].iloc[-1])
        best_score = 0.0
        note       = "No nearby zone"

        all_zones = list(context.demand_zones) + list(context.supply_zones)
        for z in all_zones:
            # Check if price is within 1.5× zone height of the zone midpoint
            proximity = abs(price - z.midpoint) / (z.height + 1e-9)
            if proximity <= 1.5:
                composite = z.strength_score * 0.6 + z.freshness_score * 0.4
                # Distance penalty: closer → higher bonus
                proximity_bonus = max(0, 1.0 - proximity / 1.5) * 20
                zone_score = min(composite + proximity_bonus, 100.0)
                if zone_score > best_score:
                    best_score = zone_score
                    note = (
                        f"{z.zone_type}: {z.bottom:.4f}–{z.top:.4f} "
                        f"(str={z.strength_score:.0f}, {z.freshness})"
                    )

        return round(best_score, 1), note

    # ─────────────────────────────────────────────────────────────────
    def _score_sr(self, context: AnalysisContext) -> tuple[float, str]:
        """
        Score based on alignment with the nearest S/R level.
        """
        ohlc = context.ohlc
        if ohlc is None:
            return 0.0, "No OHLC data"

        price     = float(ohlc["Close"].iloc[-1])
        all_levels = list(context.support_levels) + list(context.resistance_levels)

        if not all_levels:
            return 0.0, "No S/R levels detected"

        # Score the nearest level by distance
        nearest    = min(all_levels, key=lambda l: l.distance_pct)
        sr_score   = nearest.strength * max(0, 1.0 - nearest.distance_pct / 5.0)
        note       = (
            f"{nearest.level_type} @ {nearest.price:.4f} "
            f"(str={nearest.strength:.0f}, dist={nearest.distance_pct:.2f}%)"
        )

        return round(min(sr_score, 100.0), 1), note

    # ─────────────────────────────────────────────────────────────────
    def _score_momentum(self, context: AnalysisContext) -> tuple[float, str]:
        m = context.momentum
        if m is None:
            return 0.0, "No momentum data"
        score = m.score
        note  = f"Momentum: {m.direction} (RSI={m.rsi:.1f}, ADX={m.adx:.1f})"
        return score, note

    # ─────────────────────────────────────────────────────────────────
    def _score_volatility(self, context: AnalysisContext) -> tuple[float, str]:
        v = context.volatility
        if v is None:
            return 50.0, "No volatility data"
        # Normal regime is best for clean setups
        if v.regime == VOLATILITY_NORMAL:
            score = 80.0
            note  = f"Volatility: Normal (ratio={v.volatility_ratio:.2f})"
        elif v.regime == "Compressing":
            score = 65.0
            note  = f"Volatility: Compressing (potential breakout)"
        else:
            score = 40.0
            note  = f"Volatility: Expanding (ratio={v.volatility_ratio:.2f}) — wider stops"
        return score, note

    # ─────────────────────────────────────────────────────────────────
    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        w = self.weights

        trend_score,    trend_note    = self._score_trend(context)
        mtf_score,      mtf_note      = self._score_mtf(context)
        zone_score,     zone_note     = self._score_zone(context)
        sr_score,       sr_note       = self._score_sr(context)
        momentum_score, momentum_note = self._score_momentum(context)
        volatility_score, vol_note    = self._score_volatility(context)

        total = (
            trend_score    * w["trend"]
            + mtf_score    * w["mtf"]
            + zone_score   * w["zone"]
            + sr_score     * w["sr"]
            + momentum_score * w["momentum"]
            + volatility_score * w["volatility"]
        )

        context.confluence = ConfluenceScore(
            total          = round(total, 1),
            trend_score    = trend_score,
            mtf_score      = mtf_score,
            zone_score     = zone_score,
            sr_score       = sr_score,
            momentum_score = momentum_score,
            volatility_score = volatility_score,
            breakdown      = {
                "Trend":      (trend_note,    f"{trend_score:.1f}"),
                "MTF":        (mtf_note,      f"{mtf_score:.1f}"),
                "Zone":       (zone_note,     f"{zone_score:.1f}"),
                "S/R":        (sr_note,       f"{sr_score:.1f}"),
                "Momentum":   (momentum_note, f"{momentum_score:.1f}"),
                "Volatility": (vol_note,      f"{volatility_score:.1f}"),
            },
        )

        return context

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: AnalysisContext) -> None:
        c = context.confluence
        if c is None:
            print("  ConfluenceCalculator: no result.")
            return
        threshold = MIN_CONFLUENCE_SCORE
        status    = "✅ ABOVE threshold" if c.total >= threshold else "❌ BELOW threshold"
        print(f"\n── {self.name} ─────────────────────────")
        print(f"  Confluence Score : {c.total:.1f} / 100  {status}")
        print("  Breakdown:")
        for factor, (note, score) in c.breakdown.items():
            print(f"    {factor:12s} : {score:>6s} pts  — {note}")
