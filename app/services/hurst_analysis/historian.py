"""
Historical data tracker for Hurst exponent values.

This module implements the Single Responsibility Principle by focusing
solely on tracking historical Hurst exponent values for regime change detection.

The tracker maintains a rolling history for each symbol to support
regime change detection and analysis.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Final


logger = logging.getLogger(__name__)


class HistoricalDataTracker:
    """
    Tracks historical Hurst exponent values for symbols.

    This class follows the Single Responsibility Principle - it only
    stores and retrieves historical values. It does not calculate Hurst
    exponents, classify regimes, or detect changes.

    Maintains a bounded history (last N values) for each symbol to
    avoid memory issues in long-running applications.

    Attributes:
        max_history_per_symbol: Maximum number of historical values to store per symbol

    Example:
        >>> tracker = HistoricalDataTracker(max_history_per_symbol=100)
        >>> tracker.store("AAPL", datetime.now(), 0.65)
        >>> history = tracker.get_history("AAPL")
        >>> print(f"History length: {len(history)}")
    """

    def __init__(self, max_history_per_symbol: int = 100) -> None:
        """
        Initialize historical data tracker.

        Args:
            max_history_per_symbol: Maximum history size per symbol (default 100)
        """
        if max_history_per_symbol < 1:
            raise ValueError(f"max_history_per_symbol must be >= 1, got {max_history_per_symbol}")

        self.max_history_per_symbol: Final[int] = max_history_per_symbol
        self._historical_data: dict[str, list[tuple[datetime, float]]] = defaultdict(list)

    def store(self, symbol: str, timestamp: datetime, value: float) -> None:
        """
        Store a historical Hurst value.

        Values are stored in chronological order. When the history exceeds
        max_history_per_symbol, the oldest values are removed (FIFO).

        Args:
            symbol: Symbol identifier
            timestamp: Analysis timestamp
            value: Hurst exponent value

        Raises:
            ValueError: If value is not in valid range [0, 1]

        Example:
            >>> tracker = HistoricalDataTracker()
            >>> tracker.store("AAPL", datetime.now(), 0.65)
        """
        if not 0 <= value <= 1:
            raise ValueError(f"Hurst value must be in [0, 1], got {value}")

        self._historical_data[symbol].append((timestamp, value))

        # Keep only last N values to avoid memory issues
        if len(self._historical_data[symbol]) > self.max_history_per_symbol:
            self._historical_data[symbol] = self._historical_data[symbol][
                -self.max_history_per_symbol :
            ]

        logger.debug(
            f"Stored Hurst value for {symbol}: {value:.4f} at {timestamp} "
            f"(history size: {len(self._historical_data[symbol])})"
        )

    def get_history(self, symbol: str) -> list[tuple[datetime, float]]:
        """
        Get historical Hurst values for a symbol.

        Returns a copy of the history to prevent external modification
        of internal state.

        Args:
            symbol: Symbol identifier

        Returns:
            List of (timestamp, hurst_value) tuples in chronological order.
            Empty list if symbol not found.

        Example:
            >>> tracker = HistoricalDataTracker()
            >>> tracker.store("AAPL", datetime.now(), 0.65)
            >>> history = tracker.get_history("AAPL")
            >>> print(history)
        """
        # Return a copy to prevent external modification
        return list(self._historical_data.get(symbol, []))

    def get_all_symbols(self) -> list[str]:
        """
        Get all symbols with historical data.

        Returns:
            List of symbol identifiers

        Example:
            >>> tracker = HistoricalDataTracker()
            >>> tracker.store("AAPL", datetime.now(), 0.65)
            >>> symbols = tracker.get_all_symbols()
            >>> print(symbols)  # ["AAPL"]
        """
        return list(self._historical_data.keys())

    def clear_history(self, symbol: str) -> None:
        """
        Clear history for a specific symbol.

        Args:
            symbol: Symbol identifier

        Example:
            >>> tracker = HistoricalDataTracker()
            >>> tracker.store("AAPL", datetime.now(), 0.65)
            >>> tracker.clear_history("AAPL")
            >>> print(tracker.get_history("AAPL"))  # []
        """
        if symbol in self._historical_data:
            del self._historical_data[symbol]
            logger.debug(f"Cleared history for {symbol}")

    def clear_all(self) -> None:
        """
        Clear all historical data.

        Example:
            >>> tracker = HistoricalDataTracker()
            >>> tracker.clear_all()
        """
        self._historical_data.clear()
        logger.debug("Cleared all historical data")
