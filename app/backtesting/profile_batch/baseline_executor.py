"""
Baseline Backtest Executor Module

Executes baseline backtests with default parameters.
Handles both single-strategy and multi-strategy execution modes.

Responsibilities:
- Run baseline backtests with default parameters
- Execute multi-strategy backtests
- Aggregate multi-strategy results
- Handle temporary config file creation/cleanup
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
from app.backtesting.shared import MetricsDict, TempConfigManager, get_empty_metrics

if TYPE_CHECKING:
    from pathlib import Path

    from app.domain.models.input_profile import InputProfile

logger = logging.getLogger(__name__)

# Type aliases (additional ones not in shared module)
ConfigDict = dict[str, Any]
PerStrategyDict = dict[str, MetricsDict]


class BaselineBacktestExecutor:
    """
    Executes baseline backtests with default parameters.

    Supports both single-strategy and multi-strategy execution modes.
    Aggregates results from multiple strategies when in multi-strategy mode.
    """

    def __init__(self, output_dir: Path):
        """
        Initialize baseline executor.

        Args:
            output_dir: Directory for temporary config files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_baseline(
        self, profile: InputProfile, config: ConfigDict, multi_strategy: bool = False
    ) -> MetricsDict:
        """
        Run baseline backtest with default parameters.

        Args:
            profile: InputProfile
            config: Configuration dict
            multi_strategy: If True, use multi-strategy backtest mode

        Returns:
            Baseline metrics (single strategy or multi-strategy combined)
        """
        logger.info(
            f"Running baseline for {profile.objetivo_inversion.value} "
            f"({'multi-strategy' if multi_strategy else 'single-strategy'})"
        )

        # Use shared TempConfigManager for automatic cleanup
        with TempConfigManager(
            config, self.output_dir, prefix=f"temp_{profile.input_id[:8]}"
        ) as temp_config_path:
            try:
                runner = ComprehensiveBacktestRunner(str(temp_config_path))

                if multi_strategy:
                    return self._run_multi_strategy_baseline(runner, profile)
                else:
                    return self._run_single_strategy_baseline(runner, profile)

            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Baseline backtest failed: {e}", exc_info=True)
                return self._get_empty_metrics()

    def _run_single_strategy_baseline(
        self, runner: ComprehensiveBacktestRunner, profile: InputProfile
    ) -> MetricsDict:
        """Run single strategy baseline backtest."""
        baseline_results_list = runner.run_baseline_backtest()

        baseline_results = self._safe_extract_first_result(
            baseline_results_list,
            context=f"baseline backtest for {profile.objetivo_inversion.value}",
        )

        # Add combined field for consistency
        baseline_results["combined"] = baseline_results

        return baseline_results

    def _run_multi_strategy_baseline(
        self, runner: ComprehensiveBacktestRunner, profile: InputProfile
    ) -> MetricsDict:
        """Run multi-strategy baseline backtest."""
        logger.info("Executing multi-strategy baseline backtest")
        multi_strategy_results = runner.run_multi_strategy_backtest()

        # Aggregate results across strategies
        baseline_results = self.aggregate_multi_strategy_results(multi_strategy_results, profile)

        # Extract per-strategy results for reporting
        per_strategy = {}
        for result in multi_strategy_results:
            strategy_name = result.get("strategy_name", "unknown")
            if strategy_name != "combined":
                per_strategy[strategy_name] = {
                    "total_pnl": result.get("total_pnl", 0.0),
                    "return_pct": result.get("return_pct", 0.0),
                    "sharpe_ratio": result.get("sharpe_ratio", 0.0),
                    "max_drawdown": result.get("max_drawdown", 0.0),
                    "win_rate": result.get("win_rate", 0.0),
                    "total_trades": result.get("total_trades", 0),
                    "final_capital": result.get("final_capital", 0.0),
                    "capital_weight": result.get("capital_weight", 0.0),
                }

        baseline_results["per_strategy_results"] = per_strategy
        baseline_results["per_strategy_raw"] = multi_strategy_results

        logger.info(
            f"Multi-strategy baseline complete: "
            f"Combined Sharpe={baseline_results.get('sharpe_ratio', 0):.2f}, "
            f"Per-strategy results: {len(per_strategy)}"
        )

        return baseline_results

    def aggregate_multi_strategy_results(
        self, results: list[dict[str, Any]], profile: InputProfile
    ) -> MetricsDict:
        """
        Aggregate multi-strategy backtest results into combined metrics.

        Args:
            results: List of results from multi-strategy backtest
            profile: InputProfile for context

        Returns:
            Combined metrics dictionary
        """
        if not results:
            logger.warning("No results to aggregate")
            return self._get_empty_metrics()

        # Separate per-strategy and combined results
        per_strategy_results = {}
        combined_result = None

        for result in results:
            strategy_name = result.get("strategy_name", "unknown")
            if strategy_name == "combined":
                combined_result = result
            else:
                per_strategy_results[strategy_name] = result

        if combined_result:
            logger.info(
                f"Using pre-calculated combined result with {len(per_strategy_results)} strategies"
            )
            return combined_result

        if not per_strategy_results:
            logger.warning("No per-strategy results found")
            return self._get_empty_metrics()

        logger.info(f"Calculating combined metrics from {len(per_strategy_results)} strategies")

        # Calculate weighted average metrics
        total_initial_capital = float(profile.capital_initial)
        total_final_capital = 0.0
        total_pnl = 0.0
        total_trades = 0

        weighted_sharpe = 0.0
        weighted_return = 0.0
        weighted_max_dd = 0.0
        total_weight = 0.0

        for _strategy_name, result in per_strategy_results.items():
            capital_weight = result.get("capital_weight", 0.0)
            if capital_weight == 0.0:
                capital_weight = 1.0 / len(per_strategy_results)

            final_capital = result.get("final_capital", 0.0)
            total_final_capital += final_capital
            total_trades += result.get("total_trades", 0)

            weighted_sharpe += result.get("sharpe_ratio", 0.0) * capital_weight
            weighted_return += result.get("return_pct", 0.0) * capital_weight
            weighted_max_dd += result.get("max_drawdown", 0.0) * capital_weight
            total_weight += capital_weight

        # Calculate combined metrics
        total_pnl = total_final_capital - total_initial_capital
        combined_return = (
            (total_pnl / total_initial_capital * 100) if total_initial_capital > 0 else 0.0
        )

        # Normalize weighted metrics
        if total_weight > 0:
            weighted_sharpe /= total_weight
            weighted_return /= total_weight
            weighted_max_dd /= total_weight

        combined_metrics = {
            "test_type": "multi_strategy_combined",
            "test_name": f"Multi-Strategy Combined - {profile.objetivo_inversion.value}",
            "strategy_name": "combined",
            "modules_active": list(per_strategy_results.keys()),
            "learning_engine": None,
            "thresholds": {},
            "total_pnl": total_pnl,
            "return_pct": combined_return,
            "sharpe_ratio": weighted_sharpe,
            "max_drawdown": weighted_max_dd,
            "win_rate": 0.0,
            "total_trades": total_trades,
            "avg_trade_pnl": (total_pnl / total_trades) if total_trades > 0 else 0.0,
            "final_capital": total_final_capital,
            "total_initial_capital": total_initial_capital,
            "num_strategies": len(per_strategy_results),
            "per_strategy_results": per_strategy_results,
        }

        logger.info(
            f"Combined metrics: Sharpe={weighted_sharpe:.2f}, "
            f"Return={combined_return:.2f}%, Max DD={weighted_max_dd:.2f}%"
        )

        return combined_metrics

    def _safe_extract_first_result(
        self, results: list[dict[str, Any]] | None, context: str
    ) -> MetricsDict:
        """
        Safely extract the first result from a list of backtest results.

        Args:
            results: List of result dictionaries
            context: Context string for logging

        Returns:
            First result dict if valid, otherwise empty metrics dict
        """
        if results is None:
            logger.warning(f"Results is None for {context}, returning empty metrics")
            return self._get_empty_metrics()

        if not results:
            logger.warning(f"Results list is empty for {context}, returning empty metrics")
            return self._get_empty_metrics()

        if results[0] is None:
            logger.warning(f"First result is None for {context}, returning empty metrics")
            return self._get_empty_metrics()

        if not isinstance(results[0], dict):
            logger.error(f"First result is not a dict for {context}, got type {type(results[0])}")
            return self._get_empty_metrics()

        result = results[0]
        expected_fields = {"sharpe_ratio", "return_pct", "max_drawdown", "win_rate", "total_trades"}
        missing_fields = expected_fields - set(result.keys())

        if missing_fields:
            logger.warning(
                f"Result for {context} is missing expected fields: {missing_fields}. "
                f"Available fields: {set(result.keys())}"
            )

        logger.debug(f"Successfully extracted result for {context}")
        return result

    # Delegates to shared MetricsFactory (eliminates duplicate code)
    def _get_empty_metrics(self) -> MetricsDict:
        """Return empty metrics dict. Delegates to shared MetricsFactory."""
        return get_empty_metrics(include_pnl=True)
