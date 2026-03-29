"""
Position Manager service for backtesting.

This service is responsible for tracking and managing open positions
during backtesting. It acts as a pure state holder with no external
dependencies.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Callable

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Track and manage open positions during backtesting.

    This service handles:
    - Position state management
    - Position queries
    - Position updates
    - Position closure

    This is a pure state holder with no external dependencies.
    """

    def __init__(self):
        """Initialize the PositionManager with empty positions."""
        self.positions: dict[str, Decimal] = {}

    def get_position(self, symbol: str) -> Decimal:
        """
        Get current position for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Current position quantity (0 if no position)
        """
        return self.positions.get(symbol, Decimal("0"))

    def update_position(self, symbol: str, quantity_delta: Decimal) -> Decimal:
        """
        Update position for a symbol.

        Args:
            symbol: Trading symbol
            quantity_delta: Quantity change (positive for buy, negative for sell)

        Returns:
            New position quantity
        """
        current_position = self.get_position(symbol)
        new_position = current_position + quantity_delta

        # Remove position if it becomes zero or negative
        if new_position <= 0:
            self.positions[symbol] = Decimal("0")
        else:
            self.positions[symbol] = new_position

        return new_position

    def set_position(self, symbol: str, quantity: Decimal) -> None:
        """
        Set position for a symbol directly.

        Args:
            symbol: Trading symbol
            quantity: Position quantity
        """
        if quantity <= 0:
            self.positions[symbol] = Decimal("0")
        else:
            self.positions[symbol] = quantity

    def close_position(self, symbol: str) -> Decimal:
        """
        Close position for a symbol (set to zero).

        Args:
            symbol: Trading symbol

        Returns:
            Previous position quantity
        """
        previous_position = self.get_position(symbol)
        self.positions[symbol] = Decimal("0")
        return previous_position

    def has_open_position(self, symbol: str) -> bool:
        """
        Check if there is an open position for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            True if position > 0, False otherwise
        """
        return self.get_position(symbol) > 0

    def get_all_positions(self) -> dict[str, Decimal]:
        """
        Get all positions.

        Returns:
            Dictionary mapping symbol to position quantity
        """
        # Return copy to prevent external modification
        return dict(self.positions)

    def get_symbols_with_positions(self) -> list[str]:
        """
        Get list of symbols with open positions.

        Returns:
            List of symbols with position > 0
        """
        return [symbol for symbol, quantity in self.positions.items() if quantity > 0]

    def clear_all_positions(self) -> None:
        """Clear all positions (set all to zero)."""
        self.positions.clear()

    def get_total_position_count(self) -> int:
        """
        Get count of symbols with open positions.

        Returns:
            Number of symbols with position > 0
        """
        return len(self.get_symbols_with_positions())

    def get_total_position_value(self, price_func: Callable[[str], Decimal | None]) -> Decimal:
        """
        Calculate total value of all open positions.

        Args:
            price_func: Function to get current price for a symbol

        Returns:
            Total position value
        """
        total_value = Decimal("0")
        for symbol, quantity in self.positions.items():
            if quantity > 0:
                price = price_func(symbol)
                if price is not None:
                    total_value += quantity * price
        return total_value
