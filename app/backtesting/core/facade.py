"""
Facade for backtesting operations.

This module provides a simplified interface to the backtesting system,
hiding complexity and providing a clean API for running backtests.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Protocol, TypeVar

import pandas as pd

from app.backtesting.core.config_loader import BacktestConfigLoader
from app.backtesting.core.executor import BacktestExecutorFactory
from app.backtesting.core.orchestrator import BoundedResults

if TYPE_CHECKING:
    from app.backtesting.models import BacktestResult

logger = logging.getLogger(__name__)


class StrategyProtocol(Protocol):
    """Protocol for trading strategies."""

    def generate_signals(self, quotes: list[pd.DataFrame]) -> list[dict]:
        """Generate trading signals from market data."""
        ...

    @property
    def name(self) -> str:
        """Strategy name."""
        ...


class DataLoaderProtocol(Protocol):
    """Protocol for data loaders."""

    async def load_data(self, start_date: datetime, end_date: datetime) -> list:
        """Load market data for date range."""
        ...


T = TypeVar("T")
StrategyFactory = Callable[..., StrategyProtocol]


class BacktestRunnerFacade:
    """
    Simplified facade for backtesting operations.

    This facade provides a clean, simplified interface for running
    backtests without dealing with the complexity of the underlying
    orchestration and execution modules.
    """

    def __init__(self, config_path: str):
        """
        Initialize facade with configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_loader = BacktestConfigLoader(config_path)
        self.backtest_config = self.config_loader.get_backtest_config()
        self.results = BoundedResults(maxlen=1000)
        self.backtest_results_objects: list[tuple] = []

        # Output directory
        output_dir_config = self.config_loader.get_reporting_config()
        self.output_dir = Path(output_dir_config.get("output_directory", "reports"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Data loading (delegated)
        self.quotes: list[pd.DataFrame] = []
        self.data_loader: DataLoaderProtocol | None = None

        logger.info(
            "BacktestRunnerFacade initialized",
            extra={
                "operation": "facade_init",
                "config_path": str(config_path),
            },
        )

    async def load_data(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> None:
        """
        Load market data for backtesting.

        Args:
            start_date: Start date for data (from config if None)
            end_date: End date for data (from config if None)
        """
        from app.backtesting.data_loader import DataLoader

        input_config = self.config_loader.get_input_config()

        if start_date is None:
            start_date = datetime.strptime(input_config["start_date"], "%Y-%m-%d")
        if end_date is None:
            end_date = datetime.strptime(input_config["end_date"], "%Y-%m-%d")

        self.data_loader = DataLoader()
        self.quotes = await self._load_portfolio_market_data(start_date, end_date)

        logger.info(
            "Market data loaded for backtesting",
            extra={
                "operation": "load_data",
                "quotes_count": len(self.quotes),
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        )

    async def _load_portfolio_market_data(
        self, start_date: datetime, end_date: datetime
    ) -> list[pd.DataFrame]:
        """Load market data for portfolio symbols."""
        from app.services.portfolio_builder import PortfolioBuilder
        from app.services.portfolio_config_manager import get_portfolio_config_manager

        portfolio_config = get_portfolio_config_manager()
        portfolio_builder = PortfolioBuilder(
            portfolio_config=portfolio_config, data_loader=self.data_loader
        )

        quotes: list[pd.DataFrame] = await portfolio_builder.build_portfolio_quotes(
            start_date=start_date, end_date=end_date
        )
        return quotes

    def run_baseline(
        self, strategy: StrategyProtocol, strategy_name: str | None = None
    ) -> dict[str, float | int | str]:
        """
        Run baseline backtest.

        Args:
            strategy: Trading strategy instance
            strategy_name: Optional strategy name

        Returns:
            Result dictionary with metrics
        """
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()

        if strategy_name is None:
            strategy_name = getattr(strategy, "name", "baseline")

        strategy_class = strategy.__class__.__name__

        self._log_backtest_start(timestamp, "baseline", strategy_name, strategy_class)

        executor = BacktestExecutorFactory.create(self.backtest_config)
        result = executor.execute(self.quotes, strategy, strategy_name=strategy_name)

        result_dict = self._result_to_dict(result, "baseline", strategy_name)
        self._store_result(result_dict, result)

        execution_time = time.perf_counter() - start_time
        self._log_backtest_complete(execution_time, "baseline", strategy_name, result_dict)

        return result_dict

    def _log_backtest_start(
        self, timestamp: str, test_type: str, strategy_name: str, strategy_class: str
    ) -> None:
        """Log backtest execution start with structured context."""
        config_summary = self._get_config_summary()
        logger.info(
            "Backtest execution started",
            extra={
                "audit_type": "backtest_start",
                "timestamp": timestamp,
                "test_type": test_type,
                "strategy_name": strategy_name,
                "strategy_class": strategy_class,
                "config_summary": config_summary,
            },
        )

    def _log_backtest_complete(
        self,
        execution_time: float,
        test_type: str,
        strategy_name: str,
        result_dict: dict[str, float | int | str],
    ) -> None:
        """Log backtest execution completion with results summary."""
        results_summary = self._get_results_summary(result_dict)
        logger.info(
            "Backtest execution completed",
            extra={
                "audit_type": "backtest_complete",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_type": test_type,
                "strategy_name": strategy_name,
                "execution_time_seconds": round(execution_time, 3),
                "results_summary": results_summary,
            },
        )

    def _get_config_summary(self) -> dict[str, float]:
        """Get configuration summary for logging."""
        return {
            "initial_capital": float(self.backtest_config.initial_capital),
            "commission": float(self.backtest_config.commission_per_trade),
        }

    def _get_results_summary(
        self, result_dict: dict[str, float | int | str]
    ) -> dict[str, float | int]:
        """Get results summary for logging."""
        return {
            "total_pnl": float(result_dict["total_pnl"]),
            "return_pct": float(result_dict["return_pct"]),
            "sharpe_ratio": float(result_dict["sharpe_ratio"]),
            "total_trades": int(result_dict["total_trades"]),
            "win_rate": float(result_dict["win_rate"]),
            "max_drawdown": float(result_dict["max_drawdown"]),
        }

    def _store_result(self, result_dict: dict[str, float | int | str], result) -> None:
        """Store result in both storage containers."""
        self.results.add(result_dict)
        self.backtest_results_objects.append((result_dict["test_name"], result))

    def run_strategy_test(
        self,
        strategy: StrategyProtocol,
        test_name: str,
        test_type: str = "custom",
        **metadata: str | int | float,
    ) -> dict[str, float | int | str]:
        """
        Run custom strategy backtest.

        Args:
            strategy: Trading strategy instance
            test_name: Name for this test
            test_type: Type of test (for categorization)
            **metadata: Additional metadata to store

        Returns:
            Result dictionary with metrics
        """
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()
        strategy_class = strategy.__class__.__name__
        metadata_keys = list(metadata.keys()) if metadata else []

        self._log_custom_backtest_start(
            timestamp, test_type, test_name, strategy_class, metadata_keys
        )

        executor = BacktestExecutorFactory.create(self.backtest_config)
        result = executor.execute(self.quotes, strategy, strategy_name=test_name)

        result_dict = self._result_to_dict(result, test_type, test_name)
        result_dict.update(metadata)

        self._store_result(result_dict, result)

        execution_time = time.perf_counter() - start_time
        self._log_backtest_complete(execution_time, test_type, test_name, result_dict)

        return result_dict

    def _log_custom_backtest_start(
        self,
        timestamp: str,
        test_type: str,
        test_name: str,
        strategy_class: str,
        metadata_keys: list[str],
    ) -> None:
        """Log custom backtest execution start with metadata context."""
        logger.info(
            "Backtest execution started",
            extra={
                "audit_type": "backtest_start",
                "timestamp": timestamp,
                "test_type": test_type,
                "test_name": test_name,
                "strategy_class": strategy_class,
                "metadata_keys": metadata_keys,
                "metadata_count": len(metadata_keys),
            },
        )

    def run_parameter_sweep(
        self,
        strategy_factory: StrategyFactory,
        parameters: dict[str, list[str | int | float]],
        test_name_prefix: str = "param_sweep",
    ) -> list[dict[str, float | int | str]]:
        """
        Run parameter sweep across multiple parameter combinations.

        Args:
            strategy_factory: Callable that creates strategy from parameters
            parameters: Dictionary of parameter names to value lists
            test_name_prefix: Prefix for test names

        Returns:
            List of result dictionaries
        """
        import itertools

        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat()

        param_names = list(parameters.keys())
        param_values = [parameters[k] for k in param_names]
        total_combinations = len(list(itertools.product(*param_values)))

        self._log_parameter_sweep_start(timestamp, test_name_prefix, total_combinations, parameters)

        results = self._execute_parameter_combinations(
            strategy_factory, param_names, param_values, test_name_prefix, total_combinations
        )

        execution_time = time.perf_counter() - start_time
        self._log_parameter_sweep_complete(execution_time, test_name_prefix, results)

        return results

    def _log_parameter_sweep_start(
        self,
        timestamp: str,
        test_name_prefix: str,
        total_combinations: int,
        parameters: dict[str, list[str | int | float]],
    ) -> None:
        """Log parameter sweep start with structured context."""
        param_names = list(parameters.keys())
        logger.info(
            "Parameter sweep started",
            extra={
                "audit_type": "parameter_sweep_start",
                "timestamp": timestamp,
                "test_name_prefix": test_name_prefix,
                "parameter_combinations_count": total_combinations,
                "parameter_names": param_names,
                "parameter_values_count": {k: len(v) for k, v in parameters.items()},
            },
        )

    def _execute_parameter_combinations(
        self,
        strategy_factory: StrategyFactory,
        param_names: list[str],
        param_values: list[list[str | int | float]],
        test_name_prefix: str,
        total_combinations: int,
    ) -> list[dict[str, float | int | str]]:
        """Execute all parameter combinations and return results."""
        import itertools

        results = []
        for i, combination in enumerate(itertools.product(*param_values)):
            params = dict(zip(param_names, combination))
            logger.info(
                "Testing parameter combination",
                extra={
                    "combination_index": i + 1,
                    "total_combinations": total_combinations,
                    "parameters": params,
                },
            )

            strategy = strategy_factory(**params)
            param_str = "_".join(f"{k}={v}" for k, v in params.items())
            test_name = f"{test_name_prefix}_{param_str}"

            result_dict = self.run_strategy_test(
                strategy, test_name, test_type="parameter_sweep", **params
            )
            results.append(result_dict)

        return results

    def _log_parameter_sweep_complete(
        self,
        execution_time: float,
        test_name_prefix: str,
        results: list[dict[str, float | int | str]],
    ) -> None:
        """Log parameter sweep completion with summary."""
        best_result = max(results, key=lambda r: r.get("sharpe_ratio", 0)) if results else None
        best_result_summary = self._get_best_result_summary(best_result) if best_result else None

        logger.info(
            "Parameter sweep completed",
            extra={
                "audit_type": "parameter_sweep_complete",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_name_prefix": test_name_prefix,
                "total_results": len(results),
                "execution_time_seconds": round(execution_time, 3),
                "best_result_summary": best_result_summary,
            },
        )

    def _get_best_result_summary(
        self, result: dict[str, float | int | str]
    ) -> dict[str, float | int | str | dict[str, float | int | str]]:
        """Get summary of best result for logging."""
        params_raw = result.get("parameters", {})
        parameters: dict[str, float | int | str] = (
            params_raw if isinstance(params_raw, dict) else {}
        )
        return {
            "test_name": result.get("test_name", ""),
            "sharpe_ratio": float(result.get("sharpe_ratio", 0)),
            "total_pnl": float(result.get("total_pnl", 0)),
            "return_pct": float(result.get("return_pct", 0)),
            "parameters": parameters,
        }

    def get_results(self) -> pd.DataFrame:
        """
        Get all results as DataFrame.

        Returns:
            DataFrame with all backtest results
        """
        results_list = self.results.get_all()
        if not results_list:
            return pd.DataFrame()

        df = pd.DataFrame(results_list)

        # Sort by Sharpe ratio if available
        if "sharpe_ratio" in df.columns:
            df = df.sort_values("sharpe_ratio", ascending=False)

        return df

    def save_results(self, output_formats: list[str] | None = None) -> None:
        """
        Save results to files.

        Args:
            output_formats: List of formats ('csv', 'json'). None for config default.
        """
        if output_formats is None:
            reporting_config = self.config_loader.get_reporting_config()
            output_formats = reporting_config.get("output_format", ["csv"])

        df = self.get_results()
        if df.empty:
            logger.warning("No results to save")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if "csv" in output_formats:
            csv_path = self.output_dir / f"backtest_results_{timestamp}.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"Results saved to CSV: {csv_path}")

        if "json" in output_formats:
            json_path = self.output_dir / f"backtest_results_{timestamp}.json"
            import json

            with open(json_path, "w") as f:
                json.dump(self.results.get_all(), f, indent=2, default=str)
            logger.info(f"Results saved to JSON: {json_path}")

    def _result_to_dict(
        self, result, test_type: str, test_name: str
    ) -> dict[str, float | int | str]:
        """Convert BacktestResult to dictionary."""
        from app.backtesting.core.error_handling import BacktestResultError
        from app.backtesting.models import BacktestResult

        if not isinstance(result, BacktestResult):
            raise BacktestResultError(
                f"Expected BacktestResult, got {type(result).__name__}",
                test_type=test_type,
                test_name=test_name,
            )

        initial_capital = float(self.backtest_config.initial_capital)
        final_capital = float(result.final_capital)

        return {
            "test_type": test_type,
            "test_name": test_name,
            "strategy_name": result.strategy_name,
            "total_pnl": final_capital - initial_capital,
            "return_pct": self._calculate_return_pct(initial_capital, final_capital),
            "final_capital": final_capital,
            "total_trades": self._get_total_trades(result),
            "win_rate": self._get_win_rate(result),
            "sharpe_ratio": self._get_sharpe_ratio(result),
            "sortino_ratio": self._get_sortino_ratio(result),
            "max_drawdown": self._get_max_drawdown(result),
            "avg_trade_pnl": self._calculate_avg_trade_pnl(initial_capital, final_capital, result),
        }

    def _calculate_return_pct(self, initial_capital: float, final_capital: float) -> float:
        """Calculate return percentage."""
        return (
            ((final_capital - initial_capital) / initial_capital * 100)
            if initial_capital > 0
            else 0.0
        )

    def _get_total_trades(self, result: BacktestResult) -> int:
        """Get total trades from result."""
        return result.performance.total_trades if result.performance else 0

    def _get_win_rate(self, result: BacktestResult) -> float:
        """Get win rate from result."""
        return float(result.performance.win_rate) if result.performance else 0.0

    def _get_sharpe_ratio(self, result: BacktestResult) -> float:
        """Get Sharpe ratio from result."""
        if result.performance and result.performance.sharpe_ratio:
            return float(result.performance.sharpe_ratio)
        return 0.0

    def _get_sortino_ratio(self, result: BacktestResult) -> float:
        """Get Sortino ratio from result."""
        if result.performance and result.performance.sortino_ratio:
            return float(result.performance.sortino_ratio)
        return 0.0

    def _get_max_drawdown(self, result: BacktestResult) -> float:
        """Get max drawdown from result."""
        return float(result.performance.max_drawdown_percentage) if result.performance else 0.0

    def _calculate_avg_trade_pnl(
        self,
        initial_capital: float,
        final_capital: float,
        result: BacktestResult,
    ) -> float:
        """Calculate average trade PnL."""
        if result.performance and result.performance.total_trades > 0:
            return (final_capital - initial_capital) / result.performance.total_trades
        return 0.0

    def get_best_result(self, metric: str = "sharpe_ratio") -> dict[str, float | int | str] | None:
        """
        Get best result by metric.

        Args:
            metric: Metric name ('sharpe_ratio', 'total_pnl', etc.)

        Returns:
            Best result dictionary or None
        """
        results = self.results.get_all()
        if not results:
            return None

        return max(results, key=lambda r: r.get(metric, 0))

    def clear_results(self) -> None:
        """Clear all stored results."""
        self.results.clear()
        self.backtest_results_objects.clear()
        logger.info("Results cleared")


def create_backtest_runner(config_path: str) -> BacktestRunnerFacade:
    """
    Factory function to create backtest runner.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        BacktestRunnerFacade instance
    """
    return BacktestRunnerFacade(config_path)
