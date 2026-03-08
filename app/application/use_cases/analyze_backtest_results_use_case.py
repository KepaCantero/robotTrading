"""
Analyze Backtest Results Use Case - Application layer for result analysis

This use case provides analysis capabilities for backtest results,
including performance metrics, risk assessment, and comparison.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import numpy as np
import structlog

from ...domain.repositories.backtest_repository import BacktestRepository

logger = structlog.get_logger(__name__)


class AnalyzeBacktestResultsUseCase:
    """
    Use case for analyzing backtest results.

    Provides methods for analyzing and comparing backtest results,
    calculating additional metrics, and generating insights.
    """

    def __init__(self, backtest_repository: BacktestRepository):
        """
        Initialize use case with required dependencies.

        Args:
            backtest_repository: Repository for backtest persistence
        """
        self._backtest_repository = backtest_repository

    def get_performance_summary(self, backtest_id: str) -> dict[str, Any] | None:
        """
        Get performance summary for a backtest.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Performance summary dictionary or None
        """
        logger = structlog.get_logger(__name__)
        logger.info("get_performance_summary.entry", backtest_id=backtest_id)

        backtest = self._backtest_repository.find_by_id(backtest_id)
        if not backtest or not backtest.result:
            logger.warning("get_performance_summary.backtest_not_found", backtest_id=backtest_id)
            return None

        result = backtest.result
        summary = {
            'backtest_id': backtest_id,
            'total_return': str(result.total_return_pct),
            'sharpe_ratio': str(result.sharpe_ratio) if result.sharpe_ratio else None,
            'max_drawdown': str(result.max_drawdown) if result.max_drawdown else None,
            'win_rate': str(result.win_rate) if result.win_rate else None,
            'total_trades': result.total_trades,
            'is_profitable': result.is_profitable,
        }
        logger.info("get_performance_summary.success", backtest_id=backtest_id)
        return summary

    def compare_backtests(self, backtest_ids: list[str]) -> dict[str, Any] | None:
        """
        Compare multiple backtests.

        Args:
            backtest_ids: List of backtest identifiers to compare

        Returns:
            Comparison dictionary or None if backtests not found
        """
        logger = structlog.get_logger(__name__)
        logger.info("compare_backtests.entry", backtest_ids=backtest_ids)

        backtests = []
        for backtest_id in backtest_ids:
            backtest = self._backtest_repository.find_by_id(backtest_id)
            if backtest and backtest.result:
                backtests.append(backtest)

        if not backtests:
            logger.warning("compare_backtests.no_valid_backtests", backtest_ids=backtest_ids)
            return None

        # Calculate comparison metrics
        returns = [bt.result.total_return_pct for bt in backtests]
        sharpe_ratios = [bt.result.sharpe_ratio for bt in backtests if bt.result.sharpe_ratio]
        drawdowns = [bt.result.max_drawdown for bt in backtests if bt.result.max_drawdown]

        comparison = {
            'backtest_count': len(backtests),
            'avg_return': str(np.mean(returns)),
            'best_return': str(max(returns)),
            'worst_return': str(min(returns)),
            'avg_sharpe': str(np.mean(sharpe_ratios)) if sharpe_ratios else None,
            'avg_drawdown': str(np.mean(drawdowns)) if drawdowns else None,
            'best_backtest': max(
                backtest_ids,
                key=lambda bid: backtests[backtest_ids.index(bid)].result.total_return_pct,
            ),
        }
        logger.info("compare_backtests.success", backtest_count=len(backtests))
        return comparison

    def get_risk_metrics(self, backtest_id: str) -> dict[str, Any] | None:
        """
        Get risk metrics for a backtest.

        Args:
            backtest_id: Backtest identifier

        Returns:
            Risk metrics dictionary or None
        """
        logger = structlog.get_logger(__name__)
        logger.info("get_risk_metrics.entry", backtest_id=backtest_id)

        backtest = self._backtest_repository.find_by_id(backtest_id)
        if not backtest or not backtest.result:
            logger.warning("get_risk_metrics.backtest_not_found", backtest_id=backtest_id)
            return None

        result = backtest.result
        risk_metrics = {
            'backtest_id': backtest_id,
            'max_drawdown': str(result.max_drawdown) if result.max_drawdown else None,
            'volatility': str(result.volatility) if result.volatility else None,
            'var_95': str(result.var_95) if result.var_95 else None,
            'sortino_ratio': str(result.sortino_ratio) if result.sortino_ratio else None,
            'calmar_ratio': str(result.calmar_ratio) if result.calmar_ratio else None,
            'tail_ratio': str(result.tail_ratio) if result.tail_ratio else None,
        }
        logger.info("get_risk_metrics.success", backtest_id=backtest_id)
        return risk_metrics

    def assess_acceptable_risk(
        self, backtest_id: str, max_drawdown_threshold: Decimal = Decimal('0.20')
    ) -> dict[str, Any] | None:
        """
        Assess if backtest results are within acceptable risk parameters.

        Args:
            backtest_id: Backtest identifier
            max_drawdown_threshold: Maximum acceptable drawdown

        Returns:
            Risk assessment dictionary or None
        """
        logger = structlog.get_logger(__name__)
        logger.info(
            "assess_acceptable_risk.entry",
            backtest_id=backtest_id,
            max_drawdown_threshold=str(max_drawdown_threshold),
        )

        backtest = self._backtest_repository.find_by_id(backtest_id)
        if not backtest or not backtest.result:
            logger.warning("assess_acceptable_risk.backtest_not_found", backtest_id=backtest_id)
            return None

        result = backtest.result
        is_acceptable = result.has_acceptable_drawdown(max_drawdown_threshold)
        assessment = {
            'backtest_id': backtest_id,
            'is_acceptable': is_acceptable,
            'max_drawdown': str(result.max_drawdown) if result.max_drawdown else None,
            'threshold': str(max_drawdown_threshold),
            'is_profitable': result.is_profitable,
            'sharpe_ratio': str(result.sharpe_ratio) if result.sharpe_ratio else None,
        }
        logger.info(
            "assess_acceptable_risk.success",
            backtest_id=backtest_id,
            is_acceptable=is_acceptable,
            is_profitable=result.is_profitable,
        )
        return assessment
