"""
Metrics Factory - Consolidated metrics creation and manipulation.

Eliminates 6+ duplicate implementations of _get_empty_metrics across:
- profile_batch_backtester.py
- bayesian_optimizer.py
- baseline_executor.py
- optimization_validators.py (3 copies in same file!)
"""

from typing import Any, Dict, List, Optional, Union

from app.backtesting.shared.types import MetricKeys


class MetricsFactory:
    """
    Factory for creating and manipulating backtest metrics.

    Single source of truth for metric structures to ensure consistency
    across all backtesting components.
    """

    @staticmethod
    def get_empty_metrics(include_pnl: bool = True) -> Dict[str, Any]:
        """
        Return empty metrics dict with all standard fields.

        This replaces 6+ duplicate implementations across the codebase.

        Args:
            include_pnl: If True, include total_pnl and winning_trades fields

        Returns:
            Dict with zero/empty values for all metrics
        """
        metrics = {
            MetricKeys.SHARPE_RATIO: 0.0,
            MetricKeys.RETURN_PCT: 0.0,
            MetricKeys.MAX_DRAWDOWN: 0.0,
            MetricKeys.WIN_RATE: 0.0,
            MetricKeys.TOTAL_TRADES: 0,
        }

        if include_pnl:
            metrics.update(
                {
                    MetricKeys.TOTAL_PNL: 0.0,
                    MetricKeys.WINNING_TRADES: 0,
                }
            )

        return metrics

    @staticmethod
    def get_empty_optimization_result() -> Dict[str, Any]:
        """
        Return empty optimization result structure.

        Returns:
            Dict with empty optimization results
        """
        return {
            "best_params": {},
            "best_metrics": MetricsFactory.get_empty_metrics(),
            "best_value": 0.0,
            "history": [],
            "n_trials": 0,
        }

    @staticmethod
    def get_empty_validation_result() -> Dict[str, Any]:
        """
        Return empty validation result structure.

        Returns:
            Dict with empty validation results
        """
        return {
            "passed": False,
            "metrics": MetricsFactory.get_empty_metrics(),
            "details": {},
            "errors": [],
        }

    @staticmethod
    def calculate_improvement(
        baseline: Dict[str, float], optimized: Dict[str, float], metric_key: str
    ) -> float:
        """
        Calculate improvement percentage between baseline and optimized.

        Args:
            baseline: Baseline metrics dict
            optimized: Optimized metrics dict
            metric_key: Key of metric to compare

        Returns:
            Improvement percentage (positive = better, negative = worse)
        """
        baseline_val = baseline.get(metric_key, 0.0)
        optimized_val = optimized.get(metric_key, 0.0)

        if baseline_val == 0:
            return 0.0 if optimized_val == 0 else 100.0

        # For metrics where higher is better (sharpe, return, win_rate)
        if metric_key in [
            MetricKeys.SHARPE_RATIO,
            MetricKeys.TOTAL_RETURN,
            MetricKeys.RETURN_PCT,
            MetricKeys.WIN_RATE,
        ]:
            return ((optimized_val - baseline_val) / abs(baseline_val)) * 100

        # For metrics where lower is better (max_drawdown)
        if metric_key == MetricKeys.MAX_DRAWDOWN:
            return ((baseline_val - optimized_val) / abs(baseline_val)) * 100

        # Default: simple percentage change
        return ((optimized_val - baseline_val) / abs(baseline_val)) * 100

    @staticmethod
    def safe_extract_first(
        results: Optional[List[Dict[str, Any]]], context: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Safely extract first result from results list.

        Args:
            results: List of results (may be None or empty)
            context: Context for warning messages

        Returns:
            First result or empty metrics dict
        """
        if not results:
            import logging

            logging.getLogger(__name__).warning(f"No results from {context}")
            return MetricsFactory.get_empty_metrics()

        return results[0]

    @staticmethod
    def aggregate_metrics(metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate multiple metrics dicts into a single summary.

        Args:
            metrics_list: List of metrics dicts to aggregate

        Returns:
            Aggregated metrics with averages and totals
        """
        if not metrics_list:
            return MetricsFactory.get_empty_metrics()

        n = len(metrics_list)
        aggregated = {
            MetricKeys.SHARPE_RATIO: sum(m.get(MetricKeys.SHARPE_RATIO, 0) for m in metrics_list) / n,
            MetricKeys.RETURN_PCT: sum(m.get(MetricKeys.RETURN_PCT, 0) for m in metrics_list) / n,
            MetricKeys.MAX_DRAWDOWN: max(m.get(MetricKeys.MAX_DRAWDOWN, 0) for m in metrics_list),
            MetricKeys.WIN_RATE: sum(m.get(MetricKeys.WIN_RATE, 0) for m in metrics_list) / n,
            MetricKeys.TOTAL_TRADES: sum(m.get(MetricKeys.TOTAL_TRADES, 0) for m in metrics_list),
        }

        # Add optional fields if present
        if any(MetricKeys.TOTAL_PNL in m for m in metrics_list):
            aggregated[MetricKeys.TOTAL_PNL] = sum(
                m.get(MetricKeys.TOTAL_PNL, 0) for m in metrics_list
            )
            aggregated[MetricKeys.WINNING_TRADES] = sum(
                m.get(MetricKeys.WINNING_TRADES, 0) for m in metrics_list
            )

        return aggregated


# Convenience function for backward compatibility
def get_empty_metrics(include_pnl: bool = True) -> Dict[str, Any]:
    """
    Convenience function for backward compatibility.

    Replaces the _get_empty_metrics methods across the codebase.
    """
    return MetricsFactory.get_empty_metrics(include_pnl=include_pnl)
