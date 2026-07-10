from abc import ABC, abstractmethod
import pandas as pd


class BaseDetector(ABC):
    """
    Base class for all detectors in the Trading Decision System.

    Every detector:
    - Has access to the shared TradingContext
    - Stores detected events
    - Can print summaries
    - Can save outputs
    """

    def __init__(self, context):

        self.context = context
        self.events = []

    @abstractmethod
    def detect(self):
        """
        Every detector must implement this.
        """
        pass

    def add_event(self, event):
        """
        Add a detected event.
        """
        self.events.append(event.__dict__)

    def get_events(self):
        """
        Return all events as DataFrame.
        """
        return pd.DataFrame(self.events)

    def summary(self):

        df = self.get_events()

        print("\n========== Detector Summary ==========")

        print(f"Total Events : {len(df)}")

        if not df.empty:

            print("\nEvents by Type:")

            print(df["event"].value_counts())

        print("\n======================================")

    def save(self, filepath):

        df = self.get_events()

        if not df.empty:

            df.to_csv(filepath, index=False)

            print(f"\nSaved to:\n{filepath}")