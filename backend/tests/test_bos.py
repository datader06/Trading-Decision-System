from backend.app.market_structure.engine import MarketStructureEngine
from backend.app.market_structure.bos import BOSDetector


def main():

    print("=" * 60)
    print("Running Market Structure Engine")
    print("=" * 60)

    engine = MarketStructureEngine(
        "data/processed/RELIANCE_NS_1H.csv"
    )

    engine.run()

    print("\nOHLC Shape:", engine.get_ohlc().shape)
    print("Structure Shape:", engine.get_structure().shape)

    print("\n" + "=" * 60)
    print("Running BoS Detector")
    print("=" * 60)

    bos = BOSDetector(
        engine.get_ohlc(),
        engine.get_structure()
    )

    bos_df = bos.run()

    print("\n========== BOS EVENTS ==========\n")

    print(bos_df)

    print("\n========== SUMMARY ==========\n")

    bos.summary()


if __name__ == "__main__":
    main()