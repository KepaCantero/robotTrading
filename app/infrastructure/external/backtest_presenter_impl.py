"""
Backtest Presenter Implementation - Humble Object for UI/visualization

This implementation provides presentation logic for backtest results,
following the Humble Object pattern to keep UI code testable.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ...application.interfaces.backtest_presenter import BacktestPresenter
from ...application.use_cases.analyze_backtest_results_use_case import AnalyzeBacktestResultsUseCase
from ...domain.entities.backtest import Backtest
from ...domain.repositories.backtest_repository import BacktestRepository

logger = logging.getLogger(__name__)


class BacktestPresenterImpl(BacktestPresenter):
    """
    Implementation of backtest presenter for UI layer.

    This class is a humble object that formats domain entities
    for presentation in the UI layer. It contains minimal logic
    and delegates business operations to use cases.
    """

    def __init__(
        self,
        backtest_repository: BacktestRepository,
        analyzer: AnalyzeBacktestResultsUseCase,
    ):
        """
        Initialize presenter with dependencies.

        Args:
            backtest_repository: Repository for backtest data
            analyzer: Use case for analyzing results
        """
        self._backtest_repository = backtest_repository
        self._analyzer = analyzer

    def present_backtest_result(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """
        Present a single backtest result.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Presentation-ready dictionary or None
        """
        backtest = self._backtest_repository.find_by_id(backtest_id)

        if not backtest:
            return self.present_error(f"Backtest {backtest_id} not found")

        return self._format_backtest(backtest)

    def present_backtest_list(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Present a list of backtests.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of presentation-ready dictionaries
        """
        backtests = self._backtest_repository.find_all(limit=limit, offset=offset)
        return [self._format_backtest_summary(bt) for bt in backtests]

    def present_performance_summary(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """
        Present performance summary for a backtest.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Presentation-ready summary or None
        """
        summary = self._analyzer.get_performance_summary(backtest_id)

        if not summary:
            return self.present_error(f"No performance data for {backtest_id}")

        return {
            'status': 'success',
            'data': summary,
        }

    def present_comparison(self, backtest_ids: List[str]) -> Optional[Dict[str, Any]]:
        """
        Present comparison of multiple backtests.

        Args:
            backtest_ids: List of backtest identifiers to compare

        Returns:
            Presentation-ready comparison or None
        """
        comparison = self._analyzer.compare_backtests(backtest_ids)

        if not comparison:
            return self.present_error("Could not compare backtests")

        return {
            'status': 'success',
            'data': comparison,
        }

    def present_error(self, error_message: str) -> Dict[str, Any]:
        """
        Present an error message.

        Args:
            error_message: Error message to present

        Returns:
            Presentation-ready error dictionary
        """
        return {
            'status': 'error',
            'error': error_message,
        }

    def _format_backtest(self, backtest: Backtest) -> Dict[str, Any]:
        """
        Format a backtest entity for presentation.

        Args:
            backtest: Backtest entity

        Returns:
            Formatted dictionary
        """
        result = backtest.result

        return {
            'status': 'success',
            'data': {
                'backtest_id': backtest.backtest_id,
                'strategy': backtest.config.strategy_name,
                'status': backtest.status.value,
                'created_at': backtest.created_at.isoformat(),
                'started_at': backtest.started_at.isoformat() if backtest.started_at else None,
                'completed_at': (
                    backtest.completed_at.isoformat() if backtest.completed_at else None
                ),
                'duration_seconds': backtest.get_duration(),
                'results': (
                    {
                        'initial_capital': str(result.initial_capital) if result else None,
                        'final_capital': str(result.final_capital) if result else None,
                        'total_return_pct': str(result.total_return_pct) if result else None,
                        'sharpe_ratio': (
                            str(result.sharpe_ratio) if result and result.sharpe_ratio else None
                        ),
                        'max_drawdown': (
                            str(result.max_drawdown) if result and result.max_drawdown else None
                        ),
                        'total_trades': result.total_trades if result else 0,
                        'win_rate': str(result.win_rate) if result and result.win_rate else None,
                    }
                    if result
                    else None
                ),
                'error': backtest.error_message,
            },
        }

    def _format_backtest_summary(self, backtest: Backtest) -> Dict[str, Any]:
        """
        Format a backtest summary for list views.

        Args:
            backtest: Backtest entity

        Returns:
            Formatted summary dictionary
        """
        return {
            'backtest_id': backtest.backtest_id,
            'strategy': backtest.config.strategy_name,
            'status': backtest.status.value,
            'created_at': backtest.created_at.isoformat(),
            'completed_at': backtest.completed_at.isoformat() if backtest.completed_at else None,
            'total_return_pct': str(backtest.result.total_return_pct) if backtest.result else None,
            'sharpe_ratio': (
                str(backtest.result.sharpe_ratio)
                if backtest.result and backtest.result.sharpe_ratio
                else None
            ),
        }
