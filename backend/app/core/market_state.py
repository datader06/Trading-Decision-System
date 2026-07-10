from dataclasses import dataclass

from backend.app.core.constants import NEUTRAL


@dataclass
class MarketState:

    trend: str = NEUTRAL

    latest_hh_index: int | None = None
    latest_hl_index: int | None = None

    latest_lh_index: int | None = None
    latest_ll_index: int | None = None

    last_bos_index: int | None = None

    last_choch_index: int | None = None