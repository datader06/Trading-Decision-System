import pandas as pd

from backend.app.market_structure.structure import MarketStructure
from backend.app.core.market_state import MarketState


class TrendEngine:
    """
    Determines the current market trend from
    classified market structure.

    Uses:
        HH, HL -> Bullish
        LH, LL -> Bearish

    Also maintains the latest market state
    for use by other detectors.
    """

    def __init__(self, structure_df):

        self.structure_df = structure_df
        self.state = MarketState()

    # =========================================================
    # Update Market State
    # =========================================================

    def update(self, row):

        structure = row["Structure"]
        price = row["Price"]

        if structure == "HH":

            self.state.last_hh = price

        elif structure == "HL":

            self.state.last_hl = price

            # Latest HL becomes protected low
            self.state.protected_low = price

        elif structure == "LH":

            self.state.last_lh = price

            # Latest LH becomes protected high
            self.state.protected_high = price

        elif structure == "LL":

            self.state.last_ll = price

    # =========================================================
    # Determine Trend
    # =========================================================

    def determine_trend(self):

        bullish_ready = (
            self.state.last_hh is not None
            and self.state.last_hl is not None
        )

        bearish_ready = (
            self.state.last_ll is not None
            and self.state.last_lh is not None
        )

        # If both structures exist, preserve current trend.
        # Future BoS/CHOCH detectors will decide trend changes.
        if bullish_ready and bearish_ready:

            return self.state.trend

        if bullish_ready:

            return "Bullish"

        if bearish_ready:

            return "Bearish"

        return "Neutral"

    # =========================================================
    # Run Engine
    # =========================================================

    def run(self):

        history = []

        for _, row in self.structure_df.iterrows():

            self.update(row)

            self.state.trend = self.determine_trend()

            history.append({

                "Datetime": row["Datetime"],

                "Structure": row["Structure"],

                "Trend": self.state.trend,

                "Last_HH": self.state.last_hh,

                "Last_HL": self.state.last_hl,

                "Last_LH": self.state.last_lh,

                "Last_LL": self.state.last_ll,

                "Protected_High": self.state.protected_high,

                "Protected_Low": self.state.protected_low

            })

        trend_df = pd.DataFrame(history)

        return trend_df, self.state


# ============================================================
# Testing
# ============================================================

if __name__ == "__main__":

    ms = MarketStructure(
        "data/processed/RELIANCE_NS_1H.csv"
    )

    _, structure_df = ms.build()

    engine = TrendEngine(structure_df)

    trend_df, state = engine.run()

    print("\n========== TREND HISTORY ==========\n")

    print(trend_df.tail(20))

    print("\n========== FINAL MARKET STATE ==========\n")

    print(state)