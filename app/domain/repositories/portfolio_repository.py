"""
Portfolio Repository Interface - Domain layer contract

This interface defines the contract for portfolio data access.
Implementations are provided by the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.portfolio import Portfolio


class PortfolioRepository(ABC):
    """
    Portfolio repository interface.

    This abstract class defines the contract for portfolio data access.
    Implementations must NOT contain business logic - only data access.
    """

    @abstractmethod
    async def save(self, portfolio: Portfolio) -> None:
        """
        Save a portfolio.

        Args:
            portfolio: Portfolio to save
        """

    @abstractmethod
    async def find_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        """
        Find a portfolio by ID.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Portfolio if found, None otherwise
        """

    @abstractmethod
    async def find_all(self) -> List[Portfolio]:
        """
        Find all portfolios.

        Returns:
            List of all portfolios
        """

    @abstractmethod
    async def delete(self, portfolio_id: str) -> None:
        """
        Delete a portfolio.

        Args:
            portfolio_id: Portfolio ID to delete
        """

    @abstractmethod
    async def exists(self, portfolio_id: str) -> bool:
        """
        Check if portfolio exists.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            True if portfolio exists
        """
