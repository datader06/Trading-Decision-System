"""
timeframe.py
============
Timeframe definitions, ordering, and resample mappings used throughout
the multi-timeframe analysis pipeline.
"""

from __future__ import annotations
from enum import Enum


class Timeframe(Enum):
    """
    Supported analysis timeframes in descending order (highest first).

    Each member carries:
        resample_str  — pandas-compatible resample frequency string
        display_name  — human-readable label
        weight        — contribution weight in MTF alignment scoring
    """

    D1  = ("1D",  "Daily",     0.40)
    H4  = ("4h",  "4-Hour",    0.25)
    H1  = ("1h",  "1-Hour",    0.20)
    M15 = ("15min", "15-Min",  0.10)
    M5  = ("5min",  "5-Min",   0.05)

    def __init__(self, resample_str: str, display_name: str, weight: float) -> None:
        self.resample_str  = resample_str
        self.display_name  = display_name
        self.weight        = weight

    @classmethod
    def ordered(cls) -> list["Timeframe"]:
        """Return timeframes highest → lowest (for MTF cascade logic)."""
        return [cls.D1, cls.H4, cls.H1, cls.M15, cls.M5]

    @classmethod
    def from_string(cls, s: str) -> "Timeframe":
        """Look up a Timeframe by its resample string (e.g. '1h' → Timeframe.H1)."""
        for tf in cls:
            if tf.resample_str == s:
                return tf
        raise ValueError(f"Unknown timeframe string: {s!r}")

    def __str__(self) -> str:
        return self.display_name

    def __repr__(self) -> str:
        return f"Timeframe.{self.name}"
