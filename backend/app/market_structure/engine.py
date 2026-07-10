from backend.app.market_structure.structure import MarketStructure


class MarketStructureEngine:
    """
    Main engine responsible for generating market structure.
    """

    def __init__(self, csv_path):

        self.csv_path = csv_path

        self.ohlc_df = None
        self.structure_df = None

    def run(self):

        structure = MarketStructure(self.csv_path)

        self.ohlc_df, self.structure_df = structure.build()

        return self

    def get_ohlc(self):

        return self.ohlc_df

    def get_structure(self):

        return self.structure_df