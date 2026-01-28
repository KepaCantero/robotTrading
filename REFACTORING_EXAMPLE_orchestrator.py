"""
Comprehensive Backtest Runner - Main Orchestrator (Refactored)

This file demonstrates the refactored orchestrator that replaces
the 3,968-line monolithic ComprehensiveBacktestRunner with a
clean, modular implementation.

Lines extracted from original file: 1-376 (orchestration logic)
New implementation: ~200 lines (vs 3,968 original)

Clean Architecture Layer: Interface Adapters / Controllers
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.backtesting.core import BacktestConfig, BacktestConfigLoader
from app.backtesting.data_loader import DataLoader

# Refactored modules
from app.backtesting.config import (
    BacktestConfigFactory,
    MonteCarloDataGenerator,
    ParameterGridGenerator,
)
from app.backtesting.execution import BacktestExecutionEngine
from app.backtesting.aggregation import BacktestResultAggregator
from app.backtesting.validation import BacktestValidator

logger = logging.getLogger(__name__)


class BacktestOrchestrator:
    """
    Main orchestrator for comprehensive backtesting suite.

    This refactored orchestrator follows Clean Architecture principles:
    - Delegates specific tasks to specialized modules
    - Maintains single responsibility
    - Provides clear interfaces between components
    - Enables independent testing of each component

    The orchestrator is responsible only for:
    1. Loading configuration
    2. Coordinating module interactions
    3. Managing execution flow
    4. Returning aggregated results

    All specific backtest logic is delegated to the execution engine.
    All result formatting is delegated to the aggregator.
    All validation is delegated to the validator.

    Example:
        >>> orchestrator = BacktestOrchestrator('config/backtest.yaml')
        >>> results = orchestrator.run_all_backtests()
        >>> print(f"Completed {len(results)} backtests")
    """

    # Strategy name mapping from YAML to factory names
    STRATEGY_NAME_MAP = {
        'momentum_modular': 'modular_momentum',
        'mean_reversion_modular': 'mean_reversion',
        'pairs_trading_modular': 'pairs_trading',
        'dividend_screener': 'modular_momentum',
        'portfolio_optimization': 'modular_momentum',
    }

    def __init__(self, config_path: str):
        """
        Initialize orchestrator with configuration.

        Sets up all required modules following dependency injection
        pattern for testability.

        Args:
            config_path: Path to YAML configuration file
        """
        logger.info("Initializing backtest orchestrator")

        # Load configuration
        self.config_path = config_path
        self.config_loader = BacktestConfigLoader(config_path)
        self.raw_config = self.config_loader.raw_config

        # Initialize configuration factory
        self.config_factory = BacktestConfigFactory(self.raw_config)
        self.backtest_config = self.config_factory.create_backtest_config()

        # Setup output directory
        self.output_dir = Path(self.raw_config['reporting']['output_directory'])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize data loader
        self.data_loader = DataLoader()

        # Initialize execution engine
        self.execution_engine = BacktestExecutionEngine(
            self.backtest_config,
            self.data_loader
        )

        # Initialize result aggregator
        self.result_aggregator = BacktestResultAggregator(
            self.output_dir
        )

        # Initialize validator
        self.validator = BacktestValidator(self.raw_config)

        # Meta analyzer integration (optional)
        self.meta_enabled = self.raw_config.get('meta_analysis', {}).get('enabled', False)
        self.audit_trail = None
        self.learning_storage = None

        if self.meta_enabled:
            self._integrate_meta_analyzer()

        logger.info("Backtest orchestrator initialized successfully")

    def _integrate_meta_analyzer(self) -> None:
        """Integrate meta-analyzer if enabled in config."""
        try:
            from app.backtesting.meta_analyzer import integrate_meta_analyzer_with_runner

            meta = integrate_meta_analyzer_with_runner(
                runner=self,
                config_path=self.config_path,
                enable_audit=self.raw_config.get('meta_analysis', {}).get('enable_audit', True),
                enable_storage=self.raw_config.get('meta_analysis', {}).get('enable_storage', True),
                enable_analysis=self.raw_config.get('meta_analysis', {}).get('enable_analysis', True),
            )

            self.audit_trail = meta['audit_trail']
            self.learning_storage = meta['storage']

            if self.audit_trail:
                logger.info("Meta-analyzer integrated successfully")

        except Exception as e:
            logger.warning(f"Could not integrate meta_analyzer: {e}")

    def run_all_backtests(self) -> List[Dict[str, Any]]:
        """
        Execute all configured backtests.

        Iterates through enabled backtest types and executes them
        using the execution engine. Results are aggregated by the
        result aggregator.

        Returns:
            List of result dictionaries from all executed backtests
        """
        logger.info("=" * 80)
        logger.info("STARTING COMPREHENSIVE BACKTEST SUITE")
        logger.info("=" * 80)

        start_time = datetime.now()
        results = []

        # Load market data
        quotes = self._load_market_data()
        logger.info(f"Loaded {len(quotes)} quotes for backtesting")

        # Get enabled backtests from config
        backtests_config = self.raw_config.get('backtests', {})

        # Execute enabled backtests
        if backtests_config.get('baseline', {}).get('enabled', True):
            logger.info("\n" + "=" * 80)
            logger.info("BASELINE BACKTEST")
            logger.info("=" * 80)
            baseline_results = self._run_baseline_backtest(quotes)
            results.extend(baseline_results)

        if backtests_config.get('learning_engines', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("LEARNING ENGINES BACKTEST")
            logger.info("=" * 80)
            learning_results = self.execution_engine.execute_learning_engines(quotes)
            results.extend(learning_results)

        if backtests_config.get('walk_forward', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("WALK-FORWARD BACKTEST")
            logger.info("=" * 80)
            walk_forward_config = self.config_factory.get_walk_forward_config()
            walk_forward_results = self.execution_engine.execute_walk_forward(
                quotes,
                **walk_forward_config
            )
            results.append(walk_forward_results)

        if backtests_config.get('monte_carlo', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("MONTE CARLO BACKTEST")
            logger.info("=" * 80)
            monte_carlo_config = self.config_factory.get_monte_carlo_config()
            monte_carlo_results = self.execution_engine.execute_monte_carlo(
                quotes,
                **monte_carlo_config
            )
            results.extend(monte_carlo_results)

        if backtests_config.get('transformer_optimization', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("TRANSFORMER OPTIMIZATION BACKTEST")
            logger.info("=" * 80)
            transformer_results = self.execution_engine.execute_transformer_optimization(quotes)
            results.append(transformer_results)

        if backtests_config.get('ablation', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("ABLATION BACKTEST")
            logger.info("=" * 80)
            ablation_config = backtests_config.get('ablation', {})
            ablation_results = self.execution_engine.execute_ablation(
                quotes,
                ablation_config.get('modules_to_test', [])
            )
            results.extend(ablation_results)

        if backtests_config.get('grid_search', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("GRID SEARCH BACKTEST")
            logger.info("=" * 80)
            grid_search_config = self.config_factory.get_grid_search_config()
            grid_search_results = self.execution_engine.execute_grid_search(
                quotes,
                grid_search_config.get('param_grid', {})
            )
            results.append(grid_search_results)

        if backtests_config.get('out_of_sample', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("OUT-OF-SAMPLE BACKTEST")
            logger.info("=" * 80)
            oos_config = backtests_config.get('out_of_sample', {})
            oos_results = self.execution_engine.execute_out_of_sample(
                quotes,
                oos_config.get('train_ratio', 0.70)
            )
            results.append(oos_results)

        if backtests_config.get('multi_strategy', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("MULTI-STRATEGY BACKTEST")
            logger.info("=" * 80)
            multi_strategy_config = backtests_config.get('multi_strategy', {})
            multi_results = self.execution_engine.execute_multi_strategy(
                quotes,
                multi_strategy_config.get('strategies', [])
            )
            results.append(multi_results)

        if backtests_config.get('regime_test', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("REGIME TEST BACKTEST")
            logger.info("=" * 80)
            regime_config = self.config_factory.get_regime_test_config()
            regime_results = self.execution_engine.execute_regime_test(
                quotes,
                **regime_config
            )
            results.append(regime_results)

        # Save results
        self.result_aggregator.save_results(
            results,
            self.raw_config.get('reporting', {}).get('output_format', ['csv', 'json'])
        )

        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 80)
        logger.info(f"COMPREHENSIVE BACKTEST SUITE COMPLETED")
        logger.info(f"Total backtests: {len(results)}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 80)

        return results

    def run_specific_backtests(self, backtest_names: List[str]) -> List[Dict[str, Any]]:
        """
        Execute specific backtests by name.

        Args:
            backtest_names: List of backtest names to execute
                          (baseline, learning_engines, walk_forward, etc.)

        Returns:
            List of result dictionaries from executed backtests
        """
        logger.info("=" * 80)
        logger.info(f"RUNNING SPECIFIC BACKTESTS: {backtest_names}")
        logger.info("=" * 80)

        start_time = datetime.now()
        results = []

        # Load market data
        quotes = self._load_market_data()

        # Map names to execution methods
        backtest_methods = {
            'baseline': lambda: self._run_baseline_backtest(quotes),
            'learning_engines': lambda: self.execution_engine.execute_learning_engines(quotes),
            'walk_forward': lambda: [self.execution_engine.execute_walk_forward(
                quotes, **self.config_factory.get_walk_forward_config()
            )],
            'monte_carlo': lambda: self.execution_engine.execute_monte_carlo(
                quotes, **self.config_factory.get_monte_carlo_config()
            ),
            'transformer_optimization': lambda: [
                self.execution_engine.execute_transformer_optimization(quotes)
            ],
            'ablation': lambda: self.execution_engine.execute_ablation(
                quotes, self.raw_config.get('backtests', {}).get('ablation', {}).get('modules_to_test', [])
            ),
            'grid_search': lambda: [self.execution_engine.execute_grid_search(
                quotes, self.config_factory.get_grid_search_config().get('param_grid', {})
            )],
            'out_of_sample': lambda: [self.execution_engine.execute_out_of_sample(
                quotes, self.raw_config.get('backtests', {}).get('out_of_sample', {}).get('train_ratio', 0.70)
            )],
            'multi_strategy': lambda: [self.execution_engine.execute_multi_strategy(
                quotes, self.raw_config.get('backtests', {}).get('multi_strategy', {}).get('strategies', [])
            )],
            'regime_test': lambda: [self.execution_engine.execute_regime_test(
                quotes, **self.config_factory.get_regime_test_config()
            )],
        }

        for name in backtest_names:
            if name not in backtest_methods:
                logger.warning(f"Unknown backtest type: {name}")
                continue

            logger.info(f"\n{'=' * 80}")
            logger.info(f"EXECUTING: {name.upper()}")
            logger.info(f"{'=' * 80}")

            try:
                method = backtest_methods[name]
                test_results = method()
                results.extend(test_results)
            except Exception as e:
                logger.error(f"Error executing {name}: {e}", exc_info=True)

        # Save results if any
        if results:
            self.result_aggregator.save_results(
                results,
                self.raw_config.get('reporting', {}).get('output_format', ['csv', 'json'])
            )

        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 80)
        logger.info(f"SPECIFIC BACKTESTS COMPLETED")
        logger.info(f"Total backtests: {len(results)}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 80)

        return results

    def _load_market_data(self) -> List:
        """
        Load market data for backtesting.

        Returns:
            List of Quote objects
        """
        from datetime import datetime

        start_date = datetime.strptime(self.raw_config['input']['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(self.raw_config['input']['end_date'], "%Y-%m-%d")

        all_symbols = self.raw_config['input']['symbols']

        logger.info(f"Loading market data from {start_date.date()} to {end_date.date()}")
        logger.info(f"Symbols: {all_symbols}")

        quotes = []
        for symbol in all_symbols:
            symbol_quotes = self.data_loader.load_market_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )
            quotes.extend(symbol_quotes)
            logger.info(f"  Loaded {len(symbol_quotes)} quotes for {symbol}")

        return quotes

    def _run_baseline_backtest(self, quotes: List) -> List[Dict[str, Any]]:
        """
        Run baseline backtest with all modules active.

        Args:
            quotes: Market data quotes

        Returns:
            List with single baseline result dictionary
        """
        logger.info("Running baseline backtest...")

        # Create strategy
        strategy_config = self.config_factory.create_strategy_config()
        strategy = self._create_strategy(strategy_config)

        # Execute baseline
        result = self.execution_engine.execute_baseline(quotes, strategy)

        return [result]

    def _create_strategy(self, strategy_config: Dict[str, Any]):
        """
        Create strategy instance from configuration.

        Args:
            strategy_config: Strategy configuration dictionary

        Returns:
            Strategy instance
        """
        from app.strategies.momentum_modular.strategy import ModularMomentumStrategy

        return ModularMomentumStrategy(strategy_config)

    def get_results(self) -> List[Dict[str, Any]]:
        """
        Get all stored backtest results.

        Returns:
            List of all result dictionaries
        """
        return self.result_aggregator.get_all_results()

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Dictionary with memory statistics
        """
        # Delegate to execution engine for memory stats
        return self.execution_engine.get_memory_stats()


# Backward compatibility wrapper
class ComprehensiveBacktestRunner(BacktestOrchestrator):
    """
    Backward compatibility wrapper.

    Maintains the old API while using the new modular implementation.
    This class is deprecated and will be removed in a future version.
    """

    def __init__(self, config_path: str):
        import warnings
        warnings.warn(
            "ComprehensiveBacktestRunner is deprecated. "
            "Use BacktestOrchestrator instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(config_path)
