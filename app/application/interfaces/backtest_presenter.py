"""
Backtest Presenter Interface - Humble Object pattern for UI

This interface defines the contract for presenting backtest results
to the UI layer. Implementations should be thin wrappers that
delegate business logic to use cases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BacktestPresenter(ABC):
    """
    Presenter interface for backtest results (Humble Object pattern).

    This interface follows the Humble Object pattern by keeping the
    presenter logic simple and testable, delegating complex business
    logic to use cases.
    """

    @abstractmethod
    def present_backtest_result(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """
        Present a single backtest result.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Presentation-ready dictionary or None
        """
        pass

    @abstractmethod
    def present_backtest_list(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Present a list of backtests.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of presentation-ready dictionaries
        """
        pass

    @abstractmethod
    def present_performance_summary(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """
        Present performance summary for a backtest.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Presentation-ready summary or None
        """
        pass

    @abstractmethod
    def present_comparison(self, backtest_ids: List[str]) -> Optional[Dict[str, Any]]:
        """
        Present comparison of multiple backtests.

        Args:
            backtest_ids: List of backtest identifiers to compare

        Returns:
            Presentation-ready comparison or None
        """
        pass

    @abstractmethod
    def present_error(self, error_message: str) -> Dict[str, Any]:
        """
        Present an error message.

        Args:
            error_message: Error message to present

        Returns:
            Presentation-ready error dictionary
        """
        pass
