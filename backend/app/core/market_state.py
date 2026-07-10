from dataclasses import dataclass


@dataclass
class MarketState:

    trend: str = "Neutral"

    # Latest Structure
    last_hh: float | None = None
    last_hl: float | None = None
    last_lh: float | None = None
    last_ll: float | None = None

    # Protected Levels
    protected_high: float | None = None
    protected_low: float | None = None

    # Latest Events
    current_bos = None
    current_choch = None