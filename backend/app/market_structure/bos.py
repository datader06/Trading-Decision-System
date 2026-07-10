import pandas as pd

from backend.app.core.detector import BaseDetector
from backend.app.core.event import MarketEvent
from backend.app.core.constants import (
    BOS,
    BULLISH,
    BEARISH,
    HH,
    LL,
    WEAK,
    MEDIUM,
    STRONG
)


class BOSDetector(BaseDetector):
    """
    Sequential Break of Structure detector.

    Detects a BoS only when the latest confirmed
    HH or LL is broken by a candle CLOSE.
    """

    def __init__(self, ohlc_df, structure_df):

        super().__init__()

        self.ohlc_df = ohlc_df
        self.structure_df = structure_df

    # ------------------------------------------------ #

    def calculate_strength(self, close_price, level):

        pct = abs(close_price - level) / level * 100

        if pct < 0.20:
            return WEAK
        elif pct < 0.50:
            return MEDIUM

        return STRONG

    # ------------------------------------------------ #

    def detect(self):

        latest_hh = None
        latest_ll = None

        for _, row in self.structure_df.iterrows():

            structure = row["Structure"]

            # ----------------------------------------
            # Update latest HH
            # ----------------------------------------

            if structure == HH:

                latest_hh = {
                    "index": int(row["Index"]),
                    "price": float(row["Price"])
                }

                continue

            # ----------------------------------------
            # Update latest LL
            # ----------------------------------------

            if structure == LL:

                latest_ll = {
                    "index": int(row["Index"]),
                    "price": float(row["Price"])
                }

                continue

            # ----------------------------------------
            # Bullish Break
            # ----------------------------------------

            if latest_hh is not None:

                start = latest_hh["index"] + 1

                for candle_index in range(start, len(self.ohlc_df)):

                    candle = self.ohlc_df.iloc[candle_index]

                    close = float(candle["Close"])

                    if close > latest_hh["price"]:

                        event = MarketEvent(

                            event=BOS,

                            direction=BULLISH,

                            break_index=candle_index,

                            swing_index=latest_hh["index"],

                            datetime=str(candle["Datetime"]),

                            broken_level=latest_hh["price"],

                            close_price=close,

                            break_distance=close-latest_hh["price"],

                            strength=self.calculate_strength(
                                close,
                                latest_hh["price"]
                            )
                        )

                        self.add_event(event)

                        latest_hh = None

                        break

            # ----------------------------------------
            # Bearish Break
            # ----------------------------------------

            if latest_ll is not None:

                start = latest_ll["index"] + 1

                for candle_index in range(start, len(self.ohlc_df)):

                    candle = self.ohlc_df.iloc[candle_index]

                    close = float(candle["Close"])

                    if close < latest_ll["price"]:

                        event = MarketEvent(

                            event=BOS,

                            direction=BEARISH,

                            break_index=candle_index,

                            swing_index=latest_ll["index"],

                            datetime=str(candle["Datetime"]),

                            broken_level=latest_ll["price"],

                            close_price=close,

                            break_distance=latest_ll["price"]-close,

                            strength=self.calculate_strength(
                                close,
                                latest_ll["price"]
                            )
                        )

                        self.add_event(event)

                        latest_ll = None

                        break

        return self.get_events()

    # ------------------------------------------------ #

    def run(self):

        return self.detect()