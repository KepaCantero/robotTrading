"""
Backtest Repository Interface - Abstract contract for backtest persistence

This interface defines the contract for backtest data access without
specifying the implementation. Implementations are in the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.backtest import Backtest, BacktestStatus, BacktestType


class BacktestRepository(ABC):
    """
    Repository interface for backtest persistence.

    This abstract base class defines the contract that all backtest
    repository implementations must follow.
    """

    @abstractmethod
    def save(self, backtest: Backtest) -> None:
        """
        Save a backtest.

        Args:
            backtest: Backtest entity to save
        """

    @abstractmethod
    def find_by_id(self, backtest_id: str) -> Optional[Backtest]:
        """
        Find a backtest by ID.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Backtest entity or None if not found
        """

    @abstractmethod
    def find_by_status(self, status: BacktestStatus) -> List[Backtest]:
        """
        Find backtests by status.

        Args:
            status: Backtest status

        Returns:
            List of backtests with the specified status
        """

    @abstractmethod
    def find_by_type(self, backtest_type: BacktestType) -> List[Backtest]:
        """
        Find backtests by type.

        Args:
            backtest_type: Backtest type

        Returns:
            List of backtests of the specified type
        """

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> List[Backtest]:
        """
        Find all backtests with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of backtests
        """

    @abstractmethod
    def delete(self, backtest_id: str) -> bool:
        """
        Delete a backtest by ID.

        Args:
            backtest_id: Backtest identifier

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    def count_by_status(self, status: BacktestStatus) -> int:
        """
        Count backtests by status.

        Args:
            status: Backtest status

        Returns:
            Count of backtests with the specified status
        """

    @abstractmethod
    def get_recent_completed(self, limit: int = 10) -> List[Backtest]:
        """
        Get recently completed backtests.

        Args:
            limit: Maximum number of results

        Returns:
            List of recently completed backtests
        """
