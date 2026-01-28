"""
Position Repository Interface - Domain layer contract
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.portfolio import Position


class PositionRepository(ABC):
    """
    Position repository interface.

    Defines the contract for position data access.
    """

    @abstractmethod
    async def save(self, portfolio_id: str, position: Position) -> None:
        """Save a position."""
        pass

    @abstractmethod
    async def find_by_symbol(self, portfolio_id: str, symbol: str) -> Optional[Position]:
        """Find position by symbol."""
        pass

    @abstractmethod
    async def find_by_portfolio(self, portfolio_id: str) -> List[Position]:
        """Find all positions in a portfolio."""
        pass

    @abstractmethod
    async def delete(self, portfolio_id: str, symbol: str) -> None:
        """Delete a position."""
        pass
