"""
risk_manager.py
===============
RiskManager calculates position size and risk/reward for a trade.

Question answered: How much should be risked, and is the RR acceptable?

Every trade requires:
    entry       — planned entry price
    stop_loss   — invalidation level (where the thesis is wrong)
    target      — profit target (first target)
    account_size — total account equity
    risk_percent — maximum % of account to risk (e.g. 1.0 = 1%)

Outputs:
    stop_distance      — in price units
    stop_distance_pct  — as % of entry price
    risk_amount        — in currency units (account_size × risk_percent / 100)
    position_size      — units to buy/sell
    potential_reward   — in currency units
    risk_reward        — R:R ratio
    expected_value     — EV = (win_prob × reward) − (loss_prob × risk)
                         using 0.5 win probability as neutral default

Trades with R:R < MIN_RISK_REWARD are automatically flagged.
"""

from __future__ import annotations

from backend.app.core.base_analyzer import BaseAnalyzer
from backend.app.core.analysis_context import AnalysisContext
from backend.app.core.models import RiskParameters
from backend.app.core.constants import MIN_RISK_REWARD


class RiskManager(BaseAnalyzer):
    """
    Position sizing and risk/reward calculator.

    Args:
        account_size : Total account equity in base currency.
        risk_percent : Maximum risk per trade as a percentage of account (default 1.0%).
        win_prob     : Assumed win probability for EV calculation (default 0.5).
    """

    name = "RiskManager"

    def __init__(
        self,
        account_size: float = 100_000.0,
        risk_percent: float = 1.0,
        win_prob:     float = 0.5,
    ) -> None:
        self.account_size = account_size
        self.risk_percent = risk_percent
        self.win_prob     = win_prob

    # ─────────────────────────────────────────────────────────────────
    def calculate(
        self,
        entry:     float,
        stop_loss: float,
        target:    float,
    ) -> RiskParameters:
        """
        Compute full risk parameters for a single trade.

        Args:
            entry     : Entry price.
            stop_loss : Stop loss price.
            target    : First profit target.

        Returns:
            RiskParameters dataclass with all calculated values.
        """
        params = RiskParameters(
            entry        = entry,
            stop_loss    = stop_loss,
            target       = target,
            account_size = self.account_size,
            risk_percent = self.risk_percent,
        )

        stop_distance = abs(entry - stop_loss)
        if stop_distance == 0:
            return params   # invalid setup, return empty params

        reward_distance = abs(target - entry)

        risk_amount      = self.account_size * (self.risk_percent / 100)
        position_size    = risk_amount / stop_distance
        potential_reward = position_size * reward_distance
        risk_reward      = reward_distance / stop_distance

        # Expected Value = win_prob × reward − loss_prob × risk
        ev = (self.win_prob * potential_reward) - ((1 - self.win_prob) * risk_amount)

        params.stop_distance     = round(stop_distance, 4)
        params.stop_distance_pct = round(stop_distance / entry * 100, 2)
        params.risk_amount       = round(risk_amount, 2)
        params.position_size     = round(position_size, 4)
        params.potential_reward  = round(potential_reward, 2)
        params.risk_reward       = round(risk_reward, 2)
        params.expected_value    = round(ev, 2)

        return params

    # ─────────────────────────────────────────────────────────────────
    def analyze(self, context: AnalysisContext) -> AnalysisContext:
        """
        If a TradePlan exists in context, compute and attach RiskParameters.
        """
        plan = context.trade_plan
        if plan is None:
            return context

        risk_params = self.calculate(
            entry     = plan.entry_price,
            stop_loss = plan.stop_loss,
            target    = plan.target_1,
        )

        # Attach to signal if it exists
        if context.signal is not None:
            context.signal.risk_params   = risk_params
            context.signal.risk_reward   = risk_params.risk_reward

        return context

    # ─────────────────────────────────────────────────────────────────
    def print_report(self, params: RiskParameters) -> None:
        meets_rr = params.risk_reward >= MIN_RISK_REWARD
        status   = "✅ Acceptable" if meets_rr else f"❌ Below min R:R ({MIN_RISK_REWARD})"
        print(f"\n── Risk Report ──────────────────────────────")
        print(f"  Account Size     : {params.account_size:,.2f}")
        print(f"  Risk %           : {params.risk_percent:.2f}%")
        print(f"  Risk Amount      : {params.risk_amount:,.2f}")
        print(f"  Entry            : {params.entry:.4f}")
        print(f"  Stop Loss        : {params.stop_loss:.4f}  ({params.stop_distance_pct:.2f}%)")
        print(f"  Target           : {params.target:.4f}")
        print(f"  Stop Distance    : {params.stop_distance:.4f}")
        print(f"  Position Size    : {params.position_size:.4f} units")
        print(f"  Potential Reward : {params.potential_reward:,.2f}")
        print(f"  Risk/Reward      : {params.risk_reward:.2f}  {status}")
        print(f"  Expected Value   : {params.expected_value:,.2f}")
        print("─────────────────────────────────────────────")

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: AnalysisContext) -> None:
        if context.signal and context.signal.risk_params:
            self.print_report(context.signal.risk_params)
        else:
            print(f"  {self.name}: no risk parameters computed.")
