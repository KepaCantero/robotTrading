"""
TASK-MET-MULTI-1: Multi-Timeframe Confirmation Service.

Implements multi-timeframe confirmation to validate signals across different timeframes
(15m, 1h, 4h, daily) to increase signal quality and reduce false positives.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from app.domain.models.signal import Signal, SignalType

logger = logging.getLogger(__name__)


class TimeframeSignal:
    """Signal from a specific timeframe."""

    def __init__(self, signal: Signal, timeframe: str, timestamp: datetime):
        self.signal = signal
        self.timeframe = timeframe
        self.timestamp = timestamp

    def __repr__(self):
        return f"TimeframeSignal({self.signal.symbol}, {self.timeframe}, {self.signal.signal_type})"


class MultiTimeframeConfirmation:
    """
    TASK-MET-MULTI-1: Implements multi-timeframe confirmation for trading signals.

    Confirms signals by requiring agreement across multiple timeframes:
    - 15m, 1h, 4h, daily
    - Increases signal quality
    - Reduces false positives
    """

    def __init__(self, timeframes: list[str], min_confirmations: int = 2):
        """
        Initialize multi-timeframe confirmation.

        Args:
            timeframes: List of timeframes to consider (e.g., ['15m', '1h', '4h', '1d'])
            min_confirmations: Minimum number of timeframes that must agree
        """
        self.timeframes = timeframes
        self.min_confirmations = min_confirmations
        self.signal_history: dict[str, list[TimeframeSignal]] = defaultdict(list)
        self.confirmed_signals: list[dict[str, Any]] = []

    def add_signal(self, signal: Signal, timeframe: str) -> bool:
        """
        Add a signal from a specific timeframe and check for confirmation.

        Args:
            signal: Trading signal
            timeframe: Timeframe of the signal

        Returns:
            True if signal is confirmed across multiple timeframes
        """
        # Check if timeframe is valid
        if timeframe not in self.timeframes:
            logger.warning(f"Invalid timeframe: {timeframe}")
            return False

        # Store signal
        timeframe_signal = TimeframeSignal(signal, timeframe, datetime.utcnow())
        self.signal_history[signal.symbol].append(timeframe_signal)

        # Keep only recent signals (last hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        self.signal_history[signal.symbol] = [
            s for s in self.signal_history[signal.symbol] if s.timestamp > cutoff_time
        ]

        # Check for multi-timeframe confirmation
        return self._check_confirmation(signal.symbol)

    def _check_confirmation(self, symbol: str) -> bool:
        """
        Check if signals for a symbol are confirmed across multiple timeframes.

        Args:
            symbol: Symbol to check

        Returns:
            True if confirmed, False otherwise
        """
        signals = self.signal_history.get(symbol, [])
        if len(signals) < self.min_confirmations:
            return False

        # Group by signal type
        signals_by_type = defaultdict(list)
        for s in signals:
            signals_by_type[s.signal.signal_type].append(s)

        # Check if any signal type has enough confirmations
        for signal_type, signal_list in signals_by_type.items():
            if len(signal_list) >= self.min_confirmations:
                # Record confirmed signal
                self.confirmed_signals.append(
                    {
                        "symbol": symbol,
                        "signal_type": signal_type,
                        "timeframes": [s.timeframe for s in signal_list],
                        "confirmed_at": datetime.utcnow(),
                    }
                )
                logger.debug(
                    f"Signal confirmed for {symbol} ({signal_type}) across {len(signal_list)} timeframes: {[s.timeframe for s in signal_list]}"
                )
                return True

        return False

    def get_confirmed_signals(
        self, symbol: Optional[str] = None, recent_only: bool = True
    ) -> list[dict[str, Any]]:
        """
        Get confirmed signals.

        Args:
            symbol: Optional symbol to filter by
            recent_only: Only return signals from last hour

        Returns:
            List of confirmed signals
        """
        signals = self.confirmed_signals

        # Filter by symbol if specified
        if symbol:
            signals = [s for s in signals if s["symbol"] == symbol]

        # Filter by time if requested
        if recent_only:
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            signals = [s for s in signals if s["confirmed_at"] > cutoff_time]

        # Remove old signals
        if not recent_only:
            cutoff_time = datetime.utcnow() - timedelta(days=1)
            self.confirmed_signals = [
                s for s in self.confirmed_signals if s["confirmed_at"] > cutoff_time
            ]

        return signals

    def get_confirmation_stats(self) -> dict[str, Any]:
        """Get statistics about confirmations."""
        return {
            "total_confirmations": len(self.confirmed_signals),
            "confirmed_by_type": {
                signal_type.value: len(
                    [s for s in self.confirmed_signals if s["signal_type"] == signal_type]
                )
                for signal_type in SignalType
            },
            "unique_symbols": len({s["symbol"] for s in self.confirmed_signals}),
        }


# Global service instance
_multi_timeframe_service: Optional[MultiTimeframeConfirmation] = None


def get_multi_timeframe_service() -> MultiTimeframeConfirmation:
    """Get global multi-timeframe confirmation service."""
    global _multi_timeframe_service
    if _multi_timeframe_service is None:
        _multi_timeframe_service = MultiTimeframeConfirmation(
            timeframes=["15m", "1h", "4h", "1d"], min_confirmations=2
        )
    return _multi_timeframe_service
