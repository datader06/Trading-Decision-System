import pandas as pd
from dataclasses import dataclass

from backend.app.market_structure.structure import MarketStructure


# ============================================================
# Market State
# ============================================================

@dataclass
class MarketState:

    trend: str = "Neutral"

    last_hh: float | None = None
    last_hl: float | None = None

    last_lh: float | None = None
    last_ll: float | None = None

    protected_high: float | None = None
    protected_low: float | None = None


# ============================================================
# Trend Engine
# ============================================================

class TrendEngine:

    def __init__(self, structure_df):

        self.structure_df = structure_df
        self.state = MarketState()

    # --------------------------------------------------------

    def update(self, row):

        structure = row["Structure"]
        price = row["Price"]

        if structure == "HH":
            self.state.last_hh = price

        elif structure == "HL":
            self.state.last_hl = price

        elif structure == "LH":
            self.state.last_lh = price

        elif structure == "LL":
            self.state.last_ll = price

    # --------------------------------------------------------

    def determine_trend(self):

        # Bullish structure exists
        if (
            self.state.last_hh is not None
            and self.state.last_hl is not None
        ):
            return "Bullish"

        # Bearish structure exists
        elif (
            self.state.last_ll is not None
            and self.state.last_lh is not None
        ):
            return "Bearish"

        return "Neutral"

    # --------------------------------------------------------

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

                "Last_LL": self.state.last_ll

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