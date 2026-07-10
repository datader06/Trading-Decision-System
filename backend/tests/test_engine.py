from backend.app.market_structure.engine import MarketStructureEngine


engine = MarketStructureEngine(
    "data/processed/RELIANCE_NS_1H.csv"
)

engine.run()

print(engine.get_structure().head())