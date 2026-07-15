from backend.app.core.context import TradingContext
from backend.app.market_structure.structure import MarketStructure
from backend.app.events.bos import BOSDetector


context = TradingContext()

ms = MarketStructure(
    "data/processed/RELIANCE_NS_1H.csv"
)

ohlc_df, structure_df = ms.build()

context.ohlc = ohlc_df
context.structure = structure_df

detector = BOSDetector(context)

bos_df = detector.detect()

print("\n========== BOS EVENTS ==========\n")
print(bos_df)

detector.summary()