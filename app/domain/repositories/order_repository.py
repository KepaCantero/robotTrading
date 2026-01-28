"""
Order Repository Interface - Domain layer contract
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.order import Order


class OrderRepository(ABC):
    """
    Order repository interface.

    Defines the contract for order data access.
    """

    @abstractmethod
    async def save(self, order: Order) -> None:
        """Save an order."""
        pass

    @abstractmethod
    async def find_by_id(self, order_id: str) -> Optional[Order]:
        """Find order by ID."""
        pass

    @abstractmethod
    async def find_by_portfolio(self, portfolio_id: str) -> List[Order]:
        """Find all orders for a portfolio."""
        pass
