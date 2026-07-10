from dataclasses import dataclass


@dataclass
class MarketEvent:

    event: str

    direction: str

    break_index: int

    swing_index: int

    datetime: str

    broken_level: float

    close_price: float

    break_distance: float

    strength: str