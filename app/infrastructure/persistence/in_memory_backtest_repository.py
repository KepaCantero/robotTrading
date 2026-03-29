"""
In-Memory Backtest Repository Implementation

A simple in-memory implementation of the backtest repository for testing
and development. Production implementations would use databases.
"""

from __future__ import annotations

import logging

from ...domain.entities.backtest import Backtest, BacktestStatus, BacktestType
from ...domain.repositories.backtest_repository import BacktestRepository

logger = logging.getLogger(__name__)


class InMemoryBacktestRepository(BacktestRepository):
    """
    In-memory implementation of backtest repository.

    This implementation stores backtests in memory and is intended
    for testing and development purposes only.
    """

    def __init__(self):
        """Initialize in-memory repository."""
        self._backtests: dict[str, Backtest] = {}

    def save(self, backtest: Backtest) -> None:
        """
        Save a backtest.

        Args:
            backtest: Backtest entity to save
        """
        self._backtests[backtest.backtest_id] = backtest
        logger.debug(f"Saved backtest: {backtest.backtest_id}")

    def find_by_id(self, backtest_id: str) -> Backtest | None:
        """
        Find a backtest by ID.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Backtest entity or None if not found
        """
        return self._backtests.get(backtest_id)

    def find_by_status(self, status: BacktestStatus) -> list[Backtest]:
        """
        Find backtests by status.

        Args:
            status: Backtest status

        Returns:
            List of backtests with the specified status
        """
        return [bt for bt in self._backtests.values() if bt.status == status]

    def find_by_type(self, backtest_type: BacktestType) -> list[Backtest]:
        """
        Find backtests by type.

        Args:
            backtest_type: Backtest type

        Returns:
            List of backtests of the specified type
        """
        return [bt for bt in self._backtests.values() if bt.config.backtest_type == backtest_type]

    def find_all(self, limit: int = 100, offset: int = 0) -> list[Backtest]:
        """
        Find all backtests with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of backtests
        """
        backtests = list(self._backtests.values())
        # Sort by created date descending
        backtests.sort(key=lambda bt: bt.created_at, reverse=True)
        return backtests[offset : offset + limit]

    def delete(self, backtest_id: str) -> bool:
        """
        Delete a backtest by ID.

        Args:
            backtest_id: Backtest identifier

        Returns:
            True if deleted, False if not found
        """
        if backtest_id in self._backtests:
            del self._backtests[backtest_id]
            logger.debug(f"Deleted backtest: {backtest_id}")
            return True
        return False

    def count_by_status(self, status: BacktestStatus) -> int:
        """
        Count backtests by status.

        Args:
            status: Backtest status

        Returns:
            Count of backtests with the specified status
        """
        return sum(1 for bt in self._backtests.values() if bt.status == status)

    def get_recent_completed(self, limit: int = 10) -> list[Backtest]:
        """
        Get recently completed backtests.

        Args:
            limit: Maximum number of results

        Returns:
            List of recently completed backtests
        """
        completed = self.find_by_status(BacktestStatus.COMPLETED)
        # Sort by completion time descending
        completed.sort(key=lambda bt: bt.completed_at or bt.created_at, reverse=True)
        return completed[:limit]
