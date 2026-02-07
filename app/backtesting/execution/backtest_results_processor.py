"""
Backtest Results Processor - Processes and aggregates backtest results

This module is responsible for processing backtest results, calculating
aggregated metrics, and generating summaries.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ...domain.value_objects.backtest_result import BacktestResultValue

logger = logging.getLogger(__name__)


class BacktestResultsProcessor:
    """
    Processes and aggregates backtest results.

    This class is responsible for:
    - Calculating aggregate statistics across multiple runs
    - Generating performance summaries
    - Comparing results across different configurations
    """

    def __init__(self):
        """Initialize results processor."""
        self.results: List[BacktestResultValue] = []

    def add_result(self, result: BacktestResultValue) -> None:
        """
        Add a result to the processor.

        Args:
            result: Backtest result to add
        """
        self.results.append(result)
        logger.debug(
            "Added backtest result to processor",
            extra={
                "total_results": len(self.results),
                "result_return": str(result.total_return_pct),
            },
        )

    def add_results(self, results: List[BacktestResultValue]) -> None:
        """
        Add multiple results to the processor.

        Args:
            results: List of backtest results to add
        """
        self.results.extend(results)
        logger.info(
            "Added multiple backtest results to processor",
            extra={
                "results_added": len(results),
                "total_results": len(self.results),
            },
        )

    def clear(self) -> None:
        """Clear all stored results."""
        self.results.clear()

    def get_summary_statistics(self) -> Optional[Dict[str, Any]]:
        """
        Calculate summary statistics across all results.

        Returns:
            Summary statistics dictionary or None if no results
        """
        if not self.results:
            logger.debug("Summary statistics requested but no results available")
            return None

        # Extract metrics
        returns = [r.total_return_pct for r in self.results]
        sharpe_ratios = [r.sharpe_ratio for r in self.results if r.sharpe_ratio]
        max_drawdowns = [r.max_drawdown for r in self.results if r.max_drawdown]
        win_rates = [r.win_rate for r in self.results if r.win_rate]

        summary = {
            'total_runs': len(self.results),
            'returns': {
                'mean': float(np.mean(returns)),
                'std': float(np.std(returns)),
                'min': float(np.min(returns)),
                'max': float(np.max(returns)),
                'median': float(np.median(returns)),
            },
        }

        if sharpe_ratios:
            summary['sharpe_ratios'] = {
                'mean': float(np.mean([float(sr) for sr in sharpe_ratios])),
                'std': float(np.std([float(sr) for sr in sharpe_ratios])),
                'min': float(np.min([float(sr) for sr in sharpe_ratios])),
                'max': float(np.max([float(sr) for sr in sharpe_ratios])),
            }

        if max_drawdowns:
            summary['max_drawdowns'] = {
                'mean': float(np.mean([float(dd) for dd in max_drawdowns])),
                'std': float(np.std([float(dd) for dd in max_drawdowns])),
                'min': float(np.min([float(dd) for dd in max_drawdowns])),
                'max': float(np.max([float(dd) for dd in max_drawdowns])),
            }

        if win_rates:
            summary['win_rates'] = {
                'mean': float(np.mean([float(wr) for wr in win_rates])),
                'std': float(np.std([float(wr) for wr in win_rates])),
                'min': float(np.min([float(wr) for wr in win_rates])),
                'max': float(np.max([float(wr) for wr in win_rates])),
            }

        logger.info(
            "Calculated summary statistics",
            extra={
                "total_runs": len(self.results),
                "mean_return": float(summary['returns']['mean']),
            },
        )
        return summary

    def get_best_result(self, metric: str = 'total_return_pct') -> Optional[BacktestResultValue]:
        """
        Get the best result based on a metric.

        Args:
            metric: Metric to compare (default: total_return_pct)

        Returns:
            Best result or None if no results
        """
        if not self.results:
            return None

        return max(self.results, key=lambda r: getattr(r, metric, Decimal('0')))

    def get_worst_result(self, metric: str = 'total_return_pct') -> Optional[BacktestResultValue]:
        """
        Get the worst result based on a metric.

        Args:
            metric: Metric to compare (default: total_return_pct)

        Returns:
            Worst result or None if no results
        """
        if not self.results:
            return None

        return min(self.results, key=lambda r: getattr(r, metric, Decimal('0')))

    def get_percentile(
        self, percentile: float, metric: str = 'total_return_pct'
    ) -> Optional[Decimal]:
        """
        Get percentile value for a metric.

        Args:
            percentile: Percentile to calculate (0-100)
            metric: Metric to analyze

        Returns:
            Percentile value or None if no results
        """
        if not self.results:
            return None

        values = [float(getattr(r, metric, Decimal('0'))) for r in self.results]
        return Decimal(str(np.percentile(values, percentile)))

    def get_results_dataframe(self) -> Optional[pd.DataFrame]:
        """
        Convert results to pandas DataFrame for analysis.

        Returns:
            DataFrame of results or None if no results
        """
        if not self.results:
            return None

        data = []
        for i, result in enumerate(self.results):
            data.append(
                {
                    'run_id': i,
                    'total_return': float(result.total_return),
                    'total_return_pct': float(result.total_return_pct),
                    'sharpe_ratio': float(result.sharpe_ratio) if result.sharpe_ratio else None,
                    'sortino_ratio': float(result.sortino_ratio) if result.sortino_ratio else None,
                    'max_drawdown': float(result.max_drawdown) if result.max_drawdown else None,
                    'volatility': float(result.volatility) if result.volatility else None,
                    'total_trades': result.total_trades,
                    'winning_trades': result.winning_trades,
                    'losing_trades': result.losing_trades,
                    'win_rate': float(result.win_rate) if result.win_rate else None,
                }
            )

        return pd.DataFrame(data)

    def compare_to_benchmark(self, benchmark_return: Decimal) -> Optional[Dict[str, Any]]:
        """
        Compare results to a benchmark return.

        Args:
            benchmark_return: Benchmark return to compare against

        Returns:
            Comparison dictionary or None if no results
        """
        if not self.results:
            return None

        returns = [r.total_return_pct for r in self.results]
        beats_benchmark = sum(1 for r in returns if r > benchmark_return)

        return {
            'benchmark_return': str(benchmark_return),
            'total_runs': len(self.results),
            'beats_benchmark': beats_benchmark,
            'beat_percentage': beats_benchmark / len(self.results) * 100,
            'avg_excess_return': str(
                Decimal(str(np.mean([float(r) - float(benchmark_return) for r in returns])))
            ),
        }
