"""
Orchestrator for backtesting operations.

This module provides coordination and orchestration for backtesting operations,
including result management, parallel execution, and test coordination.
"""

import logging
from collections import deque
from decimal import Decimal
from threading import Lock
from typing import Any, Dict, List, Optional

from app.backtesting.models import BacktestConfig, BacktestResult

logger = logging.getLogger(__name__)


class BacktestDefaults:
    """
    Centralized backtest defaults and constants.

    This class provides a single source of truth for default values
    used across the backtesting system.

    NOTE: These defaults are used ONLY when configuration is not provided.
    Always use proper YAML configuration with risk management parameters.
    """

    COMMISSION = Decimal("10.0")  # $10 per trade (realistic)
    SLIPPAGE = Decimal("0.1")  # 0.1% slippage
    INITIAL_CAPITAL = Decimal("100000")
    MAX_POSITION_SIZE = Decimal("0.10")  # 10% of capital (conservative)
    RISK_FREE_RATE = Decimal("0.02")  # 2% annual
    STOP_LOSS_PERCENTAGE = Decimal("5.0")  # 5% stop loss
    TAKE_PROFIT_PERCENTAGE = Decimal("10.0")  # 10% take profit

    # Default metric thresholds
    SHARPE_RATIO_EXCELLENT = 2.0
    SHARPE_RATIO_GOOD = 1.0
    SHARPE_RATIO_WARNING = 0.5

    MAX_DRAWDOWN_WARNING = Decimal("-0.20")  # -20%
    MAX_DRAWDOWN_CRITICAL = Decimal("-0.50")  # -50%

    WIN_RATE_EXCELLENT = Decimal("0.60")  # 60%
    WIN_RATE_GOOD = Decimal("0.50")  # 50%
    WIN_RATE_WARNING = Decimal("0.40")  # 40%


class BoundedResults:
    """
    Thread-safe bounded results container.

    This container maintains a fixed-size collection of backtest results
    with automatic cleanup when the limit is exceeded. Thread-safe for
    concurrent execution scenarios.
    """

    def __init__(self, maxlen: int = 1000):
        """
        Initialize bounded results container.

        Args:
            maxlen: Maximum number of results to store
        """
        self._results: deque = deque(maxlen=maxlen)
        self._lock = Lock()
        self._maxlen = maxlen

    def add(self, result: Dict[str, Any]) -> None:
        """
        Add result thread-safely.

        Args:
            result: Result dictionary to add
        """
        with self._lock:
            self._results.append(result)
            self._cleanup_if_needed()

    def extend(self, results: List[Dict[str, Any]]) -> None:
        """
        Extend results thread-safely.

        Args:
            results: List of result dictionaries to add
        """
        with self._lock:
            self._results.extend(results)
            self._cleanup_if_needed()

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all results.

        Returns:
            List of all result dictionaries
        """
        with self._lock:
            return list(self._results)

    def get_latest(self, n: int) -> List[Dict[str, Any]]:
        """
        Get latest n results.

        Args:
            n: Number of latest results to retrieve

        Returns:
            List of latest result dictionaries
        """
        with self._lock:
            results_list = list(self._results)
            return results_list[-n:] if n < len(results_list) else results_list

    def clear(self) -> None:
        """Clear all results."""
        with self._lock:
            self._results.clear()

    def __len__(self) -> int:
        """Get number of results stored."""
        with self._lock:
            return len(self._results)

    def _cleanup_if_needed(self) -> None:
        """
        Cleanup old results if needed.

        This method ensures we don't exceed the configured maximum
        number of results by removing oldest entries.
        """
        target_size = int(self._maxlen * 0.8)  # Keep at 80% capacity
        while len(self._results) > target_size:
            self._results.popleft()


class OrchestrationResult:
    """
    Result from backtest orchestration.

    This class encapsulates the results of running multiple backtests,
    providing summary statistics and access to individual results.
    """

    def __init__(self, results: List[Any], config: Optional[BacktestConfig] = None):
        """
        Initialize orchestration result.

        Args:
            results: List of backtest results
            config: Optional backtest configuration used
        """
        self.results = results
        self.total = len(results)
        self.config = config
        self._summary = None

    @property
    def summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if self._summary is None:
            self._summary = self._calculate_summary()
        return self._summary

    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics from results."""
        if not self.results:
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
            }

        successful = [r for r in self.results if self._is_successful(r)]
        failed = self.total - len(successful)

        summary = {
            'total': self.total,
            'successful': len(successful),
            'failed': failed,
        }

        # Add metric statistics if we have BacktestResult objects
        if successful and isinstance(successful[0], BacktestResult):
            total_returns = [float(r.total_return) for r in successful]
            sharpe_ratios = [
                float(r.performance.sharpe_ratio)
                for r in successful
                if r.performance and r.performance.sharpe_ratio
            ]

            if total_returns:
                summary.update(
                    {
                        'avg_return': sum(total_returns) / len(total_returns),
                        'best_return': max(total_returns),
                        'worst_return': min(total_returns),
                    }
                )

            if sharpe_ratios:
                summary.update(
                    {
                        'avg_sharpe': sum(sharpe_ratios) / len(sharpe_ratios),
                        'best_sharpe': max(sharpe_ratios),
                    }
                )

        return summary

    @staticmethod
    def _is_successful(result: Any) -> bool:
        """Check if backtest result is successful."""
        # For dictionaries, any result is considered successful
        # unless explicitly marked as failed
        if isinstance(result, dict):
            return result.get('final_capital', 0) > 0
        # For BacktestResult objects, check if capital is positive
        if isinstance(result, BacktestResult):
            return result.final_capital > 0
        return False

    def get_best_result(self, metric: str = 'sharpe_ratio') -> Optional[Any]:
        """
        Get best result by metric.

        Args:
            metric: Metric name ('sharpe_ratio', 'total_return', etc.)

        Returns:
            Best BacktestResult or None
        """
        if not self.results:
            return None

        def get_metric(r: Any) -> float:
            if isinstance(r, BacktestResult):
                if metric == 'total_return':
                    return float(r.total_return)
                elif r.performance and hasattr(r.performance, metric):
                    value = getattr(r.performance, metric)
                    return float(value) if value else 0.0
            elif isinstance(r, dict):
                return float(r.get(metric, 0.0))
            return 0.0

        return max(self.results, key=get_metric)

    def filter_results(self, **criteria) -> List[Any]:
        """
        Filter results by criteria.

        Args:
            **criteria: Key-value pairs to filter by

        Returns:
            Filtered list of results
        """
        filtered = self.results

        for key, value in criteria.items():
            filtered = [r for r in filtered if isinstance(r, dict) and r.get(key) == value]

        return filtered


class BacktestOrchestrator:
    """
    Orchestrates backtesting operations.

    This coordinator manages the execution of multiple backtests,
    result collection, and provides a high-level interface for
    running backtesting workflows.
    """

    def __init__(
        self,
        config: BacktestConfig,
        executor: Optional['BacktestExecutor'] = None,
        max_results: int = 1000,
    ):
        """
        Initialize orchestrator.

        Args:
            config: Backtest configuration
            executor: Optional executor instance (created from config if None)
            max_results: Maximum number of results to store
        """
        self.config = config
        self.executor = executor
        self.results = BoundedResults(maxlen=max_results)
        self._execution_count = 0

    def run_all(self, quotes: List[Any], strategies: List[Any], **kwargs) -> OrchestrationResult:
        """
        Run all backtests with given quotes and strategies.

        Args:
            quotes: List of market data quotes
            strategies: List of trading strategy instances
            **kwargs: Additional execution parameters

        Returns:
            OrchestrationResult with all results
        """
        all_results = []

        for strategy in strategies:
            try:
                result = self._run_single(quotes, strategy, **kwargs)
                all_results.append(result)
                self.results.add(self._result_to_dict(result))
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Error executing backtest: {e}", exc_info=True)

        return OrchestrationResult(results=all_results, config=self.config)

    def _run_single(self, quotes: List[Any], strategy: Any, **kwargs) -> BacktestResult:
        """Run single backtest."""
        if self.executor is None:
            from app.backtesting.core.executor import BacktestExecutorFactory

            self.executor = BacktestExecutorFactory.create(self.config)

        self._execution_count += 1
        return self.executor.execute(quotes, strategy, **kwargs)

    @staticmethod
    def _result_to_dict(result: BacktestResult) -> Dict[str, Any]:
        """Convert BacktestResult to dictionary."""
        if not isinstance(result, BacktestResult):
            return result if isinstance(result, dict) else {}

        return {
            'strategy_name': result.strategy_name,
            'final_capital': float(result.final_capital),
            'total_return': float(result.total_return),
            'total_trades': result.performance.total_trades if result.performance else 0,
            'win_rate': float(result.performance.win_rate) if result.performance else 0.0,
            'sharpe_ratio': (
                float(result.performance.sharpe_ratio)
                if result.performance and result.performance.sharpe_ratio
                else 0.0
            ),
            'max_drawdown': (
                float(result.performance.max_drawdown_percentage) if result.performance else 0.0
            ),
        }

    @property
    def execution_count(self) -> int:
        """Get number of executions performed."""
        return self._execution_count
