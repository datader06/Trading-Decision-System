"""
signal_engine.py
================
SignalEngine is the final gate of the Decision Engine.

It collates everything from the AnalysisContext, applies the
RiskManager, and produces a definitive TradeSignal with:
    - take_trade     : bool
    - direction      : Long / Short / No Trade
    - confidence     : 0–100
    - entry / SL / target
    - risk_reward
    - reasoning      : human-readable explanation paragraph
    - confluence_breakdown

Rejection reasons (any one causes take_trade = False):
    1. Confluence score < MIN_CONFLUENCE_SCORE
    2. No valid TradePlan
    3. R:R < MIN_RISK_REWARD
    4. Direction is NO_TRADE (conflicting MTF signals)
"""

from __future__ import annotations

from backend.app.core.base_analyzer import BaseAnalyzer
from backend.app.core.analysis_context import AnalysisContext
from backend.app.core.models import TradeSignal, RiskParameters
from backend.app.core.constants import (
    LONG, SHORT, NO_TRADE,
    MIN_CONFLUENCE_SCORE,
    MIN_RISK_REWARD,
)
from backend.app.decision.risk_manager import RiskManager


class SignalEngine(BaseAnalyzer):
    """
    Final Decision Engine output stage.

    Args:
        risk_manager : RiskManager instance (configures account size / risk %).
    """

    name = "SignalEngine"

    def __init__(self, risk_manager: RiskManager | None = None) -> None:
        self.risk_manager = risk_manager or RiskManager()

    # ─────────────────────────────────────────────────────────────────
    def _build_reasoning(self, context: AnalysisContext, take: bool, reasons: list[str]) -> str:
        """Compose a human-readable paragraph explaining the signal."""
        plan = context.trade_plan
        conf = context.confluence
        t    = context.trend
        m    = context.mtf_alignment
        mom  = context.momentum
        vol  = context.volatility

        lines: list[str] = []

        if not take:
            lines.append("⚠️  No Trade — requirements not met.")
            lines.extend(f"   • {r}" for r in reasons)
            return "\n".join(lines)

        # Positive signal explanation
        direction = plan.direction if plan else NO_TRADE
        lines.append(f"✅  {direction} opportunity identified.")
        lines.append("")

        if t:
            lines.append(
                f"The primary trend is {t.direction} with {t.confidence.lower()} conviction "
                f"(strength score {t.strength:.0f}/100). "
                f"MA alignment contributes {t.ma_score:.0f}/20 pts."
            )
        if m:
            lines.append(
                f"Multi-timeframe alignment is {m.tag} (score {m.score:.0f}/100). "
                f"Per-timeframe breakdown: "
                + ", ".join(f"{tf}: {d}" for tf, d in m.per_timeframe_trend.items())
                + "."
            )
        if conf:
            lines.append(
                f"Confluence score of {conf.total:.0f}/100 is above the minimum threshold "
                f"of {MIN_CONFLUENCE_SCORE}."
            )
        if mom:
            lines.append(
                f"Momentum is {mom.direction} (RSI={mom.rsi:.1f}, ADX={mom.adx:.1f}, "
                f"{'trending' if mom.is_trending else 'ranging'} market)."
            )
        if vol:
            lines.append(
                f"Volatility regime is {vol.regime} "
                f"(ATR={vol.atr:.4f}, ratio={vol.volatility_ratio:.2f}). "
                f"Suggested stop distance: {vol.stop_suggestion:.4f}."
            )
        if plan:
            lines.append(
                f"\nTrade levels — Entry: {plan.entry_price:.4f}  |  "
                f"Stop: {plan.stop_loss:.4f}  |  "
                f"T1: {plan.target_1:.4f}  |  "
                f"T2: {plan.target_2:.4f}."
            )

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────
    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        """
        Evaluate all conditions and produce the final TradeSignal.
        """
        conf  = context.confluence
        plan  = context.trade_plan
        reasons: list[str] = []

        # ── Gate checks ───────────────────────────────────────────
        if conf is None or conf.total < MIN_CONFLUENCE_SCORE:
            threshold = MIN_CONFLUENCE_SCORE
            actual    = conf.total if conf else 0
            reasons.append(
                f"Confluence score ({actual:.0f}) is below minimum ({threshold})."
            )

        if plan is None:
            reasons.append("No trade plan generated (conflicting direction signals).")

        # Check R:R if we have a plan
        risk_params: RiskParameters | None = None
        rr = 0.0
        if plan is not None:
            risk_params = self.risk_manager.calculate(
                entry     = plan.entry_price,
                stop_loss = plan.stop_loss,
                target    = plan.target_1,
            )
            rr = risk_params.risk_reward
            if rr < MIN_RISK_REWARD:
                reasons.append(
                    f"Risk/Reward ({rr:.2f}) is below minimum ({MIN_RISK_REWARD})."
                )

        take_trade = len(reasons) == 0

        direction  = plan.direction if (plan and take_trade) else NO_TRADE
        entry      = plan.entry_price if plan else 0.0
        stop_loss  = plan.stop_loss   if plan else 0.0
        target     = plan.target_1    if plan else 0.0
        confidence = conf.total       if conf else 0.0

        reasoning = self._build_reasoning(context, take_trade, reasons)

        context.signal = TradeSignal(
            take_trade          = take_trade,
            direction           = direction,
            confidence          = confidence,
            entry               = entry,
            stop_loss           = stop_loss,
            target              = target,
            risk_reward         = rr,
            reasoning           = reasoning,
            confluence_score    = confidence,
            confluence_breakdown= conf.breakdown if conf else {},
            trade_plan          = plan,
            risk_params         = risk_params,
        )

        return context

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: AnalysisContext) -> None:
        s = context.signal
        if s is None:
            print(f"  {self.name}: no signal generated.")
            return

        print(f"\n{'═'*55}")
        print("  TRADING SIGNAL")
        print(f"{'═'*55}")
        print(s.reasoning)
        print(f"{'═'*55}")

        if s.risk_params:
            self.risk_manager.print_report(s.risk_params)
