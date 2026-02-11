"""
Trailing Stop Manager for Dynamic Exit Management.

Implements trailing stop logic that follows price favorably to capture extended trends.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TrailingStopManager:
    """
    Manages trailing stop logic for positions.

    The trailing stop follows price in the favorable direction but locks in profits
    by not moving against the position.
    """

    def __init__(self, trailing_distance_pct: float = getattr(config.trading, 'max_risk_per_trade', 0.02)):
        """
        Initialize trailing stop manager.

        Args:
            trailing_distance_pct: Percentage distance for trailing stop (default 2%)
        """
        self.trailing_distance_pct = Decimal(str(trailing_distance_pct))
        self.trailing_stops: Dict[str, Decimal] = {}  # symbol -> current_stop_price
        self.peak_prices: Dict[str, Decimal] = {}  # symbol -> peak_price

    def update_for_position(
        self,
        symbol: str,
        current_price: Decimal,
        direction: str,
        initial_stop: Optional[Decimal] = None,
    ) -> Optional[Decimal]:
        """
        Update trailing stop for a position.

        Args:
            symbol: Trading symbol
            current_price: Current market price
            direction: 'buy' or 'sell'
            initial_stop: Initial stop loss price (for long positions, this should be below entry)

        Returns:
            Current trailing stop price or None
        """
        if symbol not in self.trailing_stops:
            # Initialize with initial stop if provided
            if initial_stop:
                self.trailing_stops[symbol] = initial_stop
                self.peak_prices[symbol] = current_price
                return initial_stop
            else:
                return None

        current_stop = self.trailing_stops[symbol]
        peak_price = self.peak_prices[symbol]

        if direction == "buy":
            # For long positions: stop should trail below price
            # Update peak if price goes higher
            if current_price > peak_price:
                self.peak_prices[symbol] = current_price

            # Calculate new trailing stop
            new_stop = peak_price * (Decimal("1") - self.trailing_distance_pct)

            # Trailing stop can only move up (tighten), never down
            if new_stop > current_stop:
                self.trailing_stops[symbol] = new_stop
                logger.debug(
                    f"Updated trailing stop for {symbol}: {current_stop:.2f} -> {new_stop:.2f}"
                )

        elif direction == "sell":
            # For short positions: stop should trail above price
            # Update peak if price goes lower
            if current_price < peak_price:
                self.peak_prices[symbol] = current_price

            # Calculate new trailing stop
            new_stop = peak_price * (Decimal("1") + self.trailing_distance_pct)

            # Trailing stop can only move down (tighten), never up
            if new_stop < current_stop or symbol not in self.trailing_stops:
                self.trailing_stops[symbol] = new_stop
                logger.debug(
                    f"Updated trailing stop for {symbol}: {current_stop:.2f} -> {new_stop:.2f}"
                )

        return self.trailing_stops[symbol]

    def get_current_stop(self, symbol: str) -> Optional[Decimal]:
        """Get current trailing stop price for a symbol."""
        return self.trailing_stops.get(symbol)

    def should_exit_position(self, symbol: str, current_price: Decimal, direction: str) -> bool:
        """
        Check if trailing stop should trigger exit.

        Args:
            symbol: Trading symbol
            current_price: Current market price
            direction: 'buy' (long) or 'sell' (short)

        Returns:
            True if trailing stop is triggered, False otherwise
        """
        if symbol not in self.trailing_stops:
            return False

        stop_price = self.trailing_stops[symbol]

        if direction == "buy":
            # Exit long if price drops below trailing stop
            return current_price <= stop_price
        elif direction == "sell":
            # Exit short if price rises above trailing stop
            return current_price >= stop_price

        return False

    def remove_position(self, symbol: str) -> None:
        """Remove trailing stop tracking for a closed position."""
        if symbol in self.trailing_stops:
            del self.trailing_stops[symbol]
        if symbol in self.peak_prices:
            del self.peak_prices[symbol]
        logger.debug(f"Removed trailing stop tracking for {symbol}")

    def reset(self) -> None:
        """Reset all trailing stops."""
        self.trailing_stops.clear()
        self.peak_prices.clear()
