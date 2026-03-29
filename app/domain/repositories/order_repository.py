"""
Order Repository Interface - Domain layer contract
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.order import Order


class OrderRepository(ABC):
    """
    Order repository interface.

    Defines the contract for order data access.
    """

    @abstractmethod
    async def save(self, order: Order) -> None:
        """Save an order."""

    @abstractmethod
    async def find_by_id(self, order_id: str) -> Order | None:
        """Find order by ID."""

    @abstractmethod
    async def find_by_portfolio(self, portfolio_id: str) -> list[Order]:
        """Find all orders for a portfolio."""
