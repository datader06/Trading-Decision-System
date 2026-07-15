"""
models.py
=========
Shared dataclasses used across the Analysis Engine and Decision Engine.

Design rule: every dataclass in this file should be a pure data container —
no business logic, no dependencies on other modules.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════════════
# Market Structure
# ══════════════════════════════════════════════════════════════════════

@dataclass
class SwingPoint:
    """A single detected swing high or swing low."""

    index:      int
    datetime:   str
    swing_type: str             # "High" or "Low"
    price:      float
    structure:  str             # HH / HL / LH / LL / SH / SL
    strength:   float = 0.0     # 0–100 quality score (prominence + ATR ratio + volume)


@dataclass
class TrendResult:
    """Output of the enhanced TrendEngine."""

    direction:       str            # Bullish / Bearish / Neutral
    strength:        float          # 0–100
    confidence:      str            # Strong / Moderate / Weak
    momentum_score:  float          # 0–100
    swing_score:     float          # 0–100  (swing sequence quality)
    ma_score:        float          # 0–100  (MA alignment)
    atr_score:       float          # 0–100  (ATR expansion)
    last_hh:         Optional[float] = None
    last_hl:         Optional[float] = None
    last_lh:         Optional[float] = None
    last_ll:         Optional[float] = None
    protected_high:  Optional[float] = None
    protected_low:   Optional[float] = None


# ══════════════════════════════════════════════════════════════════════
# Support & Resistance
# ══════════════════════════════════════════════════════════════════════

@dataclass
class SupportResistanceLevel:
    """A clustered price level acting as support or resistance."""

    level_type:    str          # "Support" or "Resistance"
    price:         float
    strength:      float        # 0–100
    touch_count:   int
    last_tested:   Optional[str] = None
    distance_pct:  float = 0.0  # % distance from current price


# ══════════════════════════════════════════════════════════════════════
# Supply & Demand Zones
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Zone:
    """A supply or demand zone detected from impulsive price moves."""

    zone_type:       str            # "Supply Zone" or "Demand Zone"
    top:             float
    bottom:          float
    time_created:    str
    freshness:       str            # Fresh / Tested / Violated
    strength_score:  float          # 0–100 (impulse magnitude)
    freshness_score: float          # 0–100 (100 = never touched)
    retest_count:    int   = 0
    reaction_history: list = field(default_factory=list)

    @property
    def midpoint(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def height(self) -> float:
        return abs(self.top - self.bottom)


# ══════════════════════════════════════════════════════════════════════
# Momentum
# ══════════════════════════════════════════════════════════════════════

@dataclass
class MomentumState:
    """Output of the MomentumAnalyzer."""

    score:               float          # 0–100 composite score
    direction:           str            # Bullish Momentum / Bearish Momentum / Neutral
    rsi:                 float = 0.0
    rsi_state:           str   = ""     # Overbought / Oversold / Neutral
    macd_histogram:      float = 0.0
    macd_signal:         str   = ""     # Bullish / Bearish
    adx:                 float = 0.0
    is_trending:         bool  = False  # ADX > 25
    roc:                 float = 0.0
    is_diverging:        bool  = False


# ══════════════════════════════════════════════════════════════════════
# Volatility
# ══════════════════════════════════════════════════════════════════════

@dataclass
class VolatilityState:
    """Output of the VolatilityAnalyzer."""

    atr:              float
    atr_avg:          float
    volatility_ratio: float          # atr / atr_avg
    regime:           str            # Expanding / Normal / Compressing
    stop_suggestion:  float          # 1.5 × ATR by default


# ══════════════════════════════════════════════════════════════════════
# MTF Alignment
# ══════════════════════════════════════════════════════════════════════

@dataclass
class MTFAlignment:
    """Output of the MTFAlignmentAnalyzer."""

    score:                float           # 0–100
    tag:                  str             # Strong Bullish / Weak Bullish / Mixed / ...
    per_timeframe_trend:  dict = field(default_factory=dict)   # { "1H": "Bullish", ... }
    dominant_direction:   str  = "Neutral"


# ══════════════════════════════════════════════════════════════════════
# Decision Engine
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ConfluenceScore:
    """Weighted confluence score across all analysis factors."""

    total:              float           # 0–100
    trend_score:        float = 0.0
    mtf_score:          float = 0.0
    zone_score:         float = 0.0
    sr_score:           float = 0.0
    momentum_score:     float = 0.0
    volatility_score:   float = 0.0
    breakdown:          dict  = field(default_factory=dict)


@dataclass
class RiskParameters:
    """Risk and position sizing calculations for a single trade."""

    entry:            float
    stop_loss:        float
    target:           float
    account_size:     float
    risk_percent:     float           # e.g. 1.0 for 1%
    risk_amount:      float = 0.0
    position_size:    float = 0.0
    stop_distance:    float = 0.0
    stop_distance_pct:float = 0.0
    potential_reward: float = 0.0
    risk_reward:      float = 0.0
    expected_value:   float = 0.0


@dataclass
class TradePlan:
    """Complete trade setup generated by the TradePlanner."""

    direction:           str
    entry_type:          str            # Limit / Market / Stop
    entry_price:         float
    stop_loss:           float
    target_1:            float
    target_2:            float
    reasoning:           list = field(default_factory=list)
    confluence_score:    float = 0.0
    confluence_breakdown: dict = field(default_factory=dict)


@dataclass
class TradeSignal:
    """
    Final output of the SignalEngine.

    Contains everything needed for a trader to understand, evaluate,
    and act on a potential trade — including human-readable reasoning.
    """

    take_trade:          bool
    direction:           str
    confidence:          float           # 0–100
    entry:               float
    stop_loss:           float
    target:              float
    risk_reward:         float
    reasoning:           str             # human-readable paragraph
    confluence_score:    float
    confluence_breakdown: dict           = field(default_factory=dict)
    trade_plan:          Optional[TradePlan]  = None
    risk_params:         Optional[RiskParameters] = None

    # Extension point for future AI annotations
    ai_annotations:      dict  = field(default_factory=dict)
