import pandas as pd


class BaseDetector:
    """
    Base class for all market detectors.
    """

    def __init__(self):

        self.events = []

    def add_event(self, event):

        self.events.append(event.__dict__)

    def get_events(self):

        return pd.DataFrame(self.events)

    def summary(self):

        df = self.get_events()

        print("\n========== Detector Summary ==========")

        print(f"Total Events : {len(df)}")

        if len(df):

            print("\nEvents by Type:")

            print(df["event"].value_counts())

        print("\n======================================")

    def save(self, filepath):

        df = self.get_events()

        df.to_csv(filepath, index=False)

        print(f"\nSaved to:\n{filepath}")