"""
Facade for backtesting operations.

This module provides a simplified interface to the backtesting system,
hiding complexity and providing a clean API for running backtests.
"""

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.backtesting.core.config_loader import BacktestConfigLoader
from app.backtesting.core.executor import BacktestExecutorFactory
from app.backtesting.core.orchestrator import (
    BacktestDefaults,
    BacktestOrchestrator,
    BoundedResults,
    OrchestrationResult,
)

logger = logging.getLogger(__name__)


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
        self.backtest_results_objects: List[tuple] = []

        # Output directory
        output_dir_config = self.config_loader.get_reporting_config()
        self.output_dir = Path(output_dir_config.get('output_directory', 'reports'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Data loading (delegated)
        self.quotes: List[Any] = []
        self.data_loader = None

        logger.info(f"BacktestRunnerFacade initialized with config: {config_path}")

    def load_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
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
            start_date = datetime.strptime(input_config['start_date'], "%Y-%m-%d")
        if end_date is None:
            end_date = datetime.strptime(input_config['end_date'], "%Y-%m-%d")

        self.data_loader = DataLoader()
        self.quotes = self._load_portfolio_market_data(start_date, end_date)

        logger.info(f"Loaded {len(self.quotes)} quotes for backtesting")

    def _load_portfolio_market_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Any]:
        """Load market data for portfolio symbols."""
        from app.services.portfolio_builder import PortfolioBuilder
        from app.services.portfolio_config_manager import get_portfolio_config_manager

        portfolio_config = get_portfolio_config_manager()
        portfolio_builder = PortfolioBuilder(
            portfolio_config=portfolio_config,
            data_loader=self.data_loader
        )

        return portfolio_builder.build_portfolio_quotes(
            start_date=start_date,
            end_date=end_date
        )

    def run_baseline(
        self,
        strategy: Any,
        strategy_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run baseline backtest.

        Args:
            strategy: Trading strategy instance
            strategy_name: Optional strategy name

        Returns:
            Result dictionary with metrics
        """
        if strategy_name is None:
            strategy_name = getattr(strategy, 'name', 'baseline')

        logger.info(f"Running baseline backtest: {strategy_name}")

        executor = BacktestExecutorFactory.create(self.backtest_config)
        result = executor.execute(
            self.quotes,
            strategy,
            strategy_name=strategy_name
        )

        result_dict = self._result_to_dict(result, 'baseline', strategy_name)
        self.results.add(result_dict)
        self.backtest_results_objects.append((result_dict['test_name'], result))

        logger.info(
            f"Baseline complete: PnL=${result_dict['total_pnl']:.2f}, "
            f"Sharpe={result_dict['sharpe_ratio']:.2f}"
        )

        return result_dict

    def run_strategy_test(
        self,
        strategy: Any,
        test_name: str,
        test_type: str = 'custom',
        **metadata
    ) -> Dict[str, Any]:
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
        logger.info(f"Running {test_type} backtest: {test_name}")

        executor = BacktestExecutorFactory.create(self.backtest_config)
        result = executor.execute(
            self.quotes,
            strategy,
            strategy_name=test_name
        )

        result_dict = self._result_to_dict(result, test_type, test_name)
        result_dict.update(metadata)

        self.results.add(result_dict)
        self.backtest_results_objects.append((test_name, result))

        return result_dict

    def run_parameter_sweep(
        self,
        strategy_factory: Any,
        parameters: Dict[str, List[Any]],
        test_name_prefix: str = 'param_sweep'
    ) -> List[Dict[str, Any]]:
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

        results = []
        param_names = list(parameters.keys())
        param_values = [parameters[k] for k in param_names]
        total_combinations = len(list(itertools.product(*param_values)))

        logger.info(f"Running parameter sweep: {total_combinations} combinations")

        for i, combination in enumerate(itertools.product(*param_values)):
            params = dict(zip(param_names, combination))
            logger.info(f"Testing combination {i+1}/{total_combinations}: {params}")

            strategy = strategy_factory(**params)
            param_str = "_".join(f"{k}={v}" for k, v in params.items())
            test_name = f"{test_name_prefix}_{param_str}"

            result_dict = self.run_strategy_test(
                strategy,
                test_name,
                test_type='parameter_sweep',
                parameters=params
            )
            results.append(result_dict)

        return results

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
        if 'sharpe_ratio' in df.columns:
            df = df.sort_values('sharpe_ratio', ascending=False)

        return df

    def save_results(self, output_formats: Optional[List[str]] = None) -> None:
        """
        Save results to files.

        Args:
            output_formats: List of formats ('csv', 'json'). None for config default.
        """
        if output_formats is None:
            reporting_config = self.config_loader.get_reporting_config()
            output_formats = reporting_config.get('output_format', ['csv'])

        df = self.get_results()
        if df.empty:
            logger.warning("No results to save")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if 'csv' in output_formats:
            csv_path = self.output_dir / f"backtest_results_{timestamp}.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"Results saved to CSV: {csv_path}")

        if 'json' in output_formats:
            json_path = self.output_dir / f"backtest_results_{timestamp}.json"
            import json
            with open(json_path, 'w') as f:
                json.dump(self.results.get_all(), f, indent=2, default=str)
            logger.info(f"Results saved to JSON: {json_path}")

    def _result_to_dict(
        self,
        result: Any,
        test_type: str,
        test_name: str
    ) -> Dict[str, Any]:
        """Convert BacktestResult to dictionary."""
        from app.backtesting.models import BacktestResult

        if not isinstance(result, BacktestResult):
            return {
                'test_type': test_type,
                'test_name': test_name,
                'error': 'Invalid result type',
            }

        initial_capital = float(self.backtest_config.initial_capital)
        final_capital = float(result.final_capital)

        return {
            'test_type': test_type,
            'test_name': test_name,
            'strategy_name': result.strategy_name,
            'total_pnl': final_capital - initial_capital,
            'return_pct': ((final_capital - initial_capital) / initial_capital * 100)
            if initial_capital > 0 else 0.0,
            'final_capital': final_capital,
            'total_trades': result.performance.total_trades if result.performance else 0,
            'win_rate': float(result.performance.win_rate) if result.performance else 0.0,
            'sharpe_ratio': (
                float(result.performance.sharpe_ratio)
                if result.performance and result.performance.sharpe_ratio else 0.0
            ),
            'sortino_ratio': (
                float(result.performance.sortino_ratio)
                if result.performance and result.performance.sortino_ratio else 0.0
            ),
            'max_drawdown': (
                float(result.performance.max_drawdown_percentage)
                if result.performance else 0.0
            ),
            'avg_trade_pnl': (
                (final_capital - initial_capital) / result.performance.total_trades
                if result.performance and result.performance.total_trades > 0 else 0.0
            ),
        }

    def get_best_result(self, metric: str = 'sharpe_ratio') -> Optional[Dict[str, Any]]:
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
