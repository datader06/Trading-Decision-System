import pandas as pd

from backend.app.core.detector import BaseDetector
from backend.app.core.models import Event


class BOSDetector(BaseDetector):
    """
    Detects Break of Structure (BoS).

    A Bullish BoS occurs when price closes above
    the previous Higher High.

    A Bearish BoS occurs when price closes below
    the previous Lower Low.
    """

    def __init__(self, context):

        super().__init__(context)

    # ==========================================================
    # Strength Classification
    # ==========================================================

    def classify_strength(self, distance):

        if distance >= 7:
            return "Strong"

        elif distance >= 3:
            return "Medium"

        return "Weak"

    # ==========================================================
    # Detect BoS
    # ==========================================================

    def detect(self):

        structure_df = self.context.structure
        ohlc_df = self.context.ohlc

        self.events = []

        if structure_df is None or ohlc_df is None:
            raise ValueError(
                "TradingContext must contain OHLC and Structure data."
            )

        # ------------------------------------------------------
        # Bullish BoS
        # ------------------------------------------------------

        hh_points = structure_df[
            structure_df["Structure"] == "HH"
        ]

        for _, hh in hh_points.iterrows():

            level = hh["Price"]
            start = hh["Index"] + 1

            for i in range(start, len(ohlc_df)):

                candle = ohlc_df.iloc[i]

                if candle["Close"] > level:

                    distance = candle["Close"] - level

                    event = Event(

                        event="BoS",

                        direction="Bullish",

                        break_index=i,

                        swing_index=hh["Index"],

                        datetime=candle["Datetime"],

                        broken_level=level,

                        close_price=candle["Close"],

                        break_distance=distance,

                        strength=self.classify_strength(distance)

                    )

                    self.add_event(event)

                    # Only first break counts
                    break

        # ------------------------------------------------------
        # Bearish BoS
        # ------------------------------------------------------

        ll_points = structure_df[
            structure_df["Structure"] == "LL"
        ]

        for _, ll in ll_points.iterrows():

            level = ll["Price"]
            start = ll["Index"] + 1

            for i in range(start, len(ohlc_df)):

                candle = ohlc_df.iloc[i]

                if candle["Close"] < level:

                    distance = level - candle["Close"]

                    event = Event(

                        event="BoS",

                        direction="Bearish",

                        break_index=i,

                        swing_index=ll["Index"],

                        datetime=candle["Datetime"],

                        broken_level=level,

                        close_price=candle["Close"],

                        break_distance=distance,

                        strength=self.classify_strength(distance)

                    )

                    self.add_event(event)

                    break

        # ------------------------------------------------------
        # Remove duplicate break candles
        # ------------------------------------------------------

        bos_df = self.get_events()

        if not bos_df.empty:

            bos_df = bos_df.drop_duplicates(
                subset=[
                    "direction",
                    "break_index",
                    "broken_level"
                ]
            )

            bos_df = bos_df.sort_values("break_index")

        self.context.bos = bos_df

        return bos_df