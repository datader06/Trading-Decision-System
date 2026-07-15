"""
constants.py
============
Global constants for the Analysis Engine.

Organised by category so that every module can import
only what it needs without pulling in unrelated symbols.
"""

# ──────────────────────────────────────────────
# Trend Direction
# ──────────────────────────────────────────────
BULLISH = "Bullish"
BEARISH = "Bearish"
NEUTRAL = "Neutral"

# ──────────────────────────────────────────────
# Trend Strength Labels
# ──────────────────────────────────────────────
STRONG   = "Strong"
MODERATE = "Moderate"
WEAK     = "Weak"

# ──────────────────────────────────────────────
# Market Structure Labels
# ──────────────────────────────────────────────
HH = "HH"   # Higher High
HL = "HL"   # Higher Low
LH = "LH"   # Lower High
LL = "LL"   # Lower Low
SH = "SH"   # Initial Swing High
SL = "SL"   # Initial Swing Low

# ──────────────────────────────────────────────
# Zone Types
# ──────────────────────────────────────────────
SUPPLY_ZONE  = "Supply Zone"
DEMAND_ZONE  = "Demand Zone"
SUPPORT      = "Support"
RESISTANCE   = "Resistance"

# ──────────────────────────────────────────────
# Zone Freshness
# ──────────────────────────────────────────────
FRESH    = "Fresh"
TESTED   = "Tested"
VIOLATED = "Violated"

# ──────────────────────────────────────────────
# Momentum States
# ──────────────────────────────────────────────
MOMENTUM_BULLISH  = "Bullish Momentum"
MOMENTUM_BEARISH  = "Bearish Momentum"
MOMENTUM_NEUTRAL  = "Neutral Momentum"
OVERBOUGHT        = "Overbought"
OVERSOLD          = "Oversold"

# ──────────────────────────────────────────────
# Volatility Regimes
# ──────────────────────────────────────────────
VOLATILITY_EXPANDING    = "Expanding"
VOLATILITY_NORMAL       = "Normal"
VOLATILITY_COMPRESSING  = "Compressing"

# ──────────────────────────────────────────────
# MTF Alignment Tags
# ──────────────────────────────────────────────
STRONG_BULL = "Strong Bullish"
WEAK_BULL   = "Weak Bullish"
MIXED       = "Mixed"
WEAK_BEAR   = "Weak Bearish"
STRONG_BEAR = "Strong Bearish"

# ──────────────────────────────────────────────
# Signal / Trade
# ──────────────────────────────────────────────
LONG  = "Long"
SHORT = "Short"
NO_TRADE = "No Trade"

LIMIT_ORDER  = "Limit"
MARKET_ORDER = "Market"
STOP_ORDER   = "Stop"

# ──────────────────────────────────────────────
# Confluence Threshold
# ──────────────────────────────────────────────
MIN_CONFLUENCE_SCORE: float = 60.0   # minimum score to generate a signal
MIN_RISK_REWARD:      float = 1.5    # minimum R:R to accept a trade