class TradingContext:
    """
    Shared object used across all detectors.
    """

    def __init__(self):

        # Market Data
        self.ohlc = None

        # Swing Detection
        self.swings = None

        # Market Structure
        self.structure = None

        # Events
        self.bos = None
        self.choch = None

        # Zones
        self.order_blocks = None
        self.supply = None
        self.demand = None
        self.fvg = None

        # Strategy
        self.signals = None

        # State
        self.market_state = None