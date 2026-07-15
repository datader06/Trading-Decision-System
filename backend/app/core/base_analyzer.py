"""
base_analyzer.py
================
Abstract base class for every analysis module in the Analysis Engine.

Design contract:
    - Every analyzer receives an AnalysisContext and returns an updated AnalysisContext.
    - Analyzers must NOT have side effects outside the context object.
    - This pattern makes analyzers independently testable and pluggable.

Future AI integration:
    - ML models can implement BaseAnalyzer to replace or augment any stage.
    - The `analyze()` signature is intentionally identical across all analyzers.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.core.analysis_context import AnalysisContext


class BaseAnalyzer(ABC):
    """
    Abstract base for all Analysis Engine modules.

    Subclasses must implement:
        analyze(context) → AnalysisContext

    Optional override:
        summary(context) → prints a human-readable summary to stdout.
    """

    # ── Override this in every subclass ───────────────────────────────
    name: str = "BaseAnalyzer"

    # ─────────────────────────────────────────────────────────────────
    @abstractmethod
    def analyze(self, context: "AnalysisContext") -> "AnalysisContext":
        """
        Run this analysis module.

        Args:
            context: The shared AnalysisContext carrying all intermediate results.

        Returns:
            The same AnalysisContext object with this module's results populated.
        """
        ...

    # ─────────────────────────────────────────────────────────────────
    def summary(self, context: "AnalysisContext") -> None:
        """
        Print a short human-readable summary after analysis.
        Override in subclasses to provide meaningful output.
        """
        print(f"\n[{self.name}] analysis complete.")
