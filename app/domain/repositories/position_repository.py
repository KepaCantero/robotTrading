"""
Position Repository Interface - Domain layer contract
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.portfolio import Position


class PositionRepository(ABC):
    """
    Position repository interface.

    Defines the contract for position data access.
    """

    @abstractmethod
    async def save(self, portfolio_id: str, position: Position) -> None:
        """Save a position."""

    @abstractmethod
    async def find_by_symbol(self, portfolio_id: str, symbol: str) -> Position | None:
        """Find position by symbol."""

    @abstractmethod
    async def find_by_portfolio(self, portfolio_id: str) -> list[Position]:
        """Find all positions in a portfolio."""

    @abstractmethod
    async def delete(self, portfolio_id: str, symbol: str) -> None:
        """Delete a position."""
