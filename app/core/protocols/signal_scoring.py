"""
Protocol interface for Signal Scoring Engine.

This protocol defines the interface for signal scoring components,
allowing domain layer to depend on abstractions rather than concrete implementations.
"""

from typing import List, Protocol, runtime_checkable

from app.domain.models.signal import Signal


@runtime_checkable
class SignalScoringEngineProtocol(Protocol):
    """
    Protocol for signal scoring engine implementations.

    The signal scoring engine processes raw signals from strategies,
    applying cooldown management, compound scoring, and filtering.
    """

    def process_signals(self, signals: List[Signal], apply_cooldown: bool = True) -> List[Signal]:
        """
        Process signals through the complete scoring pipeline.

        Args:
            signals: Raw signals from strategies
            apply_cooldown: Whether to apply cooldown (False for backtesting)

        Returns:
            Processed and filtered signals
        """
        ...
