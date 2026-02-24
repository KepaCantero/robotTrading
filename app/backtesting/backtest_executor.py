"""
Backtest Executor Module - Core backtest execution logic.

Extracted from comprehensive_backtest_runner.py for Single Responsibility.
Handles execution of various backtest types:
- Baseline backtests
- Learning engine backtests
- Monte Carlo simulations
- Walk-forward validation

Architecture:
- Uses SimpleBacktestExecutor for sequential execution
- Uses ProcessPoolBacktestExecutor for parallel execution
- Integrates with AggressiveMemoryManager for results
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from app.backtesting.core.executor import SimpleBacktestExecutor
from app.backtesting.core.error_handling import train_with_retry, TrainingError, MutexError
from app.backtesting.core.memory_manager import AggressiveMemoryManager
from app.backtesting.models import BacktestConfig, BacktestResult
from app.domain.strategies.momentum_modular.strategy import ModularMomentumStrategy


class BacktestExecutor:
    """
    Handles core backtest execution logic.

    Provides methods for running different types of backtests:
    - Baseline backtests with all modules active
    - Learning engine backtests (supervised, deep, transformer)
    - Monte Carlo simulations with realistic data
    - Walk-forward validation with rolling windows
    """

    def __init__(
        self,
        backtest_config: BacktestConfig,
        memory_manager: AggressiveMemoryManager,
        raw_config: Dict[str, Any],
        quotes: List,
        parallel_enabled: bool = False,
        max_workers: Optional[int] = None,
    ):
        """
        Initialize BacktestExecutor.

        Args:
            backtest_config: Backtest configuration
            memory_manager: Memory manager for storing results
            raw_config: Raw YAML configuration
            quotes: Loaded market data quotes
            parallel_enabled: Whether parallel execution is enabled
            max_workers: Maximum number of parallel workers
        """
        self.backtest_config = backtest_config
        self.memory_manager = memory_manager
        self.raw_config = raw_config
        self.quotes = quotes
        self.parallel_enabled = parallel_enabled
        self.max_workers = max_workers

    def run_baseline_backtest(
        self,
        strategy_config: Dict[str, Any],
        thresholds_helper,
        strategy_name_helper,
        metrics_helper,
        audit_helper,
    ) -> List[Dict[str, Any]]:
        """
        Execute baseline backtest with all modules active.

        Args:
            strategy_config: Strategy configuration dict
            thresholds_helper: Helper function to extract thresholds
            strategy_name_helper: Helper function to get strategy name
            metrics_helper: Helper function to calculate metrics
            audit_helper: Helper function to save audit trail

        Returns:
            List with baseline result dictionary
        """
        logger.info("Running baseline backtest...")

        strategy = ModularMomentumStrategy(strategy_config)

        initial_capital = self.backtest_config.initial_capital
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=self.backtest_config.commission_per_trade,
            slippage_percentage=self.backtest_config.slippage_percentage,
            max_position_size=self.backtest_config.max_position_size,
            stop_loss_percentage=self.backtest_config.stop_loss_percentage,
            take_profit_percentage=self.backtest_config.take_profit_percentage,
            risk_free_rate=self.backtest_config.risk_free_rate,
        )

        strategy_name = strategy_name_helper(strategy)
        executor = SimpleBacktestExecutor(backtest_config)
        result = executor.execute(self.quotes, strategy, strategy_name=strategy_name)

        consistent_metrics = metrics_helper(result, initial_capital)

        result_dict = {
            'test_type': 'baseline',
            'test_name': 'Baseline - All Modules Active',
            'modules_active': list(self.raw_config['modules']['filters'].keys()),
            'learning_engine': None,
            'thresholds': thresholds_helper(strategy_config),
            'total_pnl': consistent_metrics['total_pnl'],
            'return_pct': consistent_metrics['return_pct'],
            'win_rate': float(result.performance.win_rate),
            'sharpe_ratio': (
                float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0
            ),
            'max_drawdown': float(result.performance.max_drawdown_percentage),
            'total_trades': result.performance.total_trades,
            'avg_trade_pnl': (
                consistent_metrics['total_pnl'] / result.performance.total_trades
                if result.performance.total_trades > 0
                else 0.0
            ),
            'final_capital': consistent_metrics['final_capital'],
        }

        self.memory_manager.add_result(result_dict)
        self.memory_manager.add_backtest_object('baseline', result)

        audit_helper(result_dict, 'baseline', strategy)

        logger.info(
            f"Baseline complete: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}"
        )

        return [result_dict]

    def run_learning_engines_backtest(
        self,
        create_strategy_config_helper,
        thresholds_helper,
        strategy_name_helper,
        metrics_helper,
        audit_helper,
    ) -> List[Dict[str, Any]]:
        """
        Execute backtests for each learning engine individually.

        Args:
            create_strategy_config_helper: Helper to create strategy config
            thresholds_helper: Helper function to extract thresholds
            strategy_name_helper: Helper function to get strategy name
            metrics_helper: Helper function to calculate metrics
            audit_helper: Helper function to save audit trail

        Returns:
            List of results for each learning engine tested
        """
        logger.info("Running learning engines backtest...")

        results = []
        learning_engines_config = self.raw_config.get('learning_engines', {})

        # Only test supervised learning engine (others cause mutex blocking)
        logger.info("Learning Engines Policy: Only 'supervised' is supported (scikit-learn)")
        logger.info("  - supervised: ENABLED (scikit-learn - no mutex issues)")
        logger.info("  - deep: DISABLED (PyTorch causes mutex.cc blocking)")
        logger.info("  - transformer: DISABLED (PyTorch causes mutex.cc blocking)")
        logger.info("  - reinforcement: DISABLED (stable-baselines3/gymnasium causes mutex.cc blocking)")

        engine_types = ['supervised']

        for engine_type in engine_types:
            if not learning_engines_config.get(engine_type, {}).get('enabled', False):
                logger.info(f"Skipping {engine_type} learning engine (disabled)")
                continue

            logger.info(f"Testing {engine_type} learning engine...")

            result_dict = self._test_learning_engine(
                engine_type=engine_type,
                create_strategy_config_helper=create_strategy_config_helper,
                thresholds_helper=thresholds_helper,
                strategy_name_helper=strategy_name_helper,
                metrics_helper=metrics_helper,
                audit_helper=audit_helper,
            )
            if result_dict:
                results.append(result_dict)

        logger.info(f"Learning engines backtest completed: {len(results)} engines tested")

        return results

    def _test_learning_engine(
        self,
        engine_type: str,
        create_strategy_config_helper,
        thresholds_helper,
        strategy_name_helper,
        metrics_helper,
        audit_helper,
    ) -> Optional[Dict[str, Any]]:
        """
        Test a specific learning engine.

        Args:
            engine_type: Type of learning engine ('supervised', 'deep', etc.)
            create_strategy_config_helper: Helper to create strategy config
            thresholds_helper: Helper function to extract thresholds
            strategy_name_helper: Helper function to get strategy name
            metrics_helper: Helper function to calculate metrics
            audit_helper: Helper function to save audit trail

        Returns:
            Result dictionary or None if failed
        """
        try:
            learning_engines_config = self.raw_config.get('learning_engines', {})
            engine_config = learning_engines_config.get(engine_type, {})

            # Build adaptive_learning config with full engine configuration
            adaptive_learning_config = {
                'enabled': engine_config.get('enabled', True),
                'engine_type': engine_type,
            }

            # Add default config for supervised learning engine
            if engine_type == 'supervised':
                adaptive_learning_config.update(
                    {
                        'algorithm': 'random_forest',
                        'feature_columns': [],
                        'target_column': 'trade_success',
                        'model_parameters': {},
                        'optimize_thresholds': False,
                        'threshold_parameters': {},
                    }
                )

            # Add any additional config parameters for the specific engine
            if 'config' in engine_config:
                adaptive_learning_config.update(engine_config['config'])

            strategy_config = create_strategy_config_helper()
            strategy_config['adaptive_learning'] = adaptive_learning_config
            strategy = ModularMomentumStrategy(strategy_config)

            # Initialize the learning engine (lazy initialization)
            strategy._initialize_learning_engine()

            # Use train_with_retry for robust training
            training_successful = train_with_retry(
                strategy=strategy,
                engine_type=engine_type,
                use_subprocess=False,
            )

            if not training_successful:
                logger.warning(f"{engine_type} learning engine training failed")
                return None

            # Execute backtest
            initial_capital = self.backtest_config.initial_capital
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=self.backtest_config.commission_per_trade,
                slippage_percentage=self.backtest_config.slippage_percentage,
                max_position_size=self.backtest_config.max_position_size,
                stop_loss_percentage=self.backtest_config.stop_loss_percentage,
                take_profit_percentage=self.backtest_config.take_profit_percentage,
                risk_free_rate=self.backtest_config.risk_free_rate,
            )

            strategy_name = strategy_name_helper(strategy)
            executor = SimpleBacktestExecutor(backtest_config)
            result = executor.execute(self.quotes, strategy, strategy_name=strategy_name)

            consistent_metrics = metrics_helper(result, initial_capital)

            result_dict = {
                'test_type': f'learning_engine_{engine_type}',
                'test_name': f'Learning Engine - {engine_type.capitalize()}',
                'modules_active': list(strategy_config.get('modules', {}).keys()),
                'learning_engine': engine_type,
                'thresholds': thresholds_helper(strategy_config),
                'total_pnl': consistent_metrics['total_pnl'],
                'return_pct': consistent_metrics['return_pct'],
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': (
                    float(result.performance.sharpe_ratio)
                    if result.performance.sharpe_ratio
                    else 0.0
                ),
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': (
                    consistent_metrics['total_pnl'] / result.performance.total_trades
                    if result.performance.total_trades > 0
                    else 0.0
                ),
                'final_capital': consistent_metrics['final_capital'],
            }

            self.memory_manager.add_result(result_dict)
            self.memory_manager.add_backtest_object(f'learning_engine_{engine_type}', result)

            audit_helper(result_dict, f'learning_engine_{engine_type}', strategy)

            logger.info(
                f"{engine_type.capitalize()} learning engine complete: "
                f"PnL=${result_dict['total_pnl']:.2f}, "
                f"Sharpe={result_dict['sharpe_ratio']:.2f}"
            )

            return result_dict

        except MutexError as e:
            logger.warning(f"Mutex error in {engine_type} learning engine: {e}")
            return None
        except TrainingError as e:
            logger.error(f"Training error in {engine_type} learning engine: {e}")
            return None
        except Exception as e:
            logger.error(f"Error testing {engine_type} learning engine: {e}", exc_info=True)
            return None

    def run_monte_carlo_backtest(
        self,
        create_strategy_config_helper,
        thresholds_helper,
        parallel: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Execute Monte Carlo / Stress Test.

        Supports sequential and parallel execution.

        Args:
            create_strategy_config_helper: Helper to create strategy config
            thresholds_helper: Helper function to extract thresholds
            parallel: If True, use ProcessPoolBacktestExecutor for parallelization

        Returns:
            List of Monte Carlo simulation results
        """
        logger.info(f"Running Monte Carlo Backtest ({'parallel' if parallel else 'sequential'})...")

        mc_config = self.raw_config['backtests']['monte_carlo']
        num_simulations = mc_config.get('num_simulations', 100)
        volatility_multiplier = mc_config.get('volatility_multiplier', {}).get('default', 1.0)

        results = []

        # Create executor according to configuration
        if parallel:
            from app.backtesting.core.executor import ProcessPoolBacktestExecutor
            executor = ProcessPoolBacktestExecutor(
                self.backtest_config, max_processes=self.max_workers or 4
            )
        else:
            executor = SimpleBacktestExecutor(self.backtest_config)

        # Create base strategy
        strategy_config = create_strategy_config_helper()
        base_strategy = ModularMomentumStrategy(strategy_config)

        # Execute simulations
        for sim_num in range(num_simulations):
            if sim_num % 10 == 0:
                logger.info(f"  Simulation {sim_num+1}/{num_simulations}...")

            # Create modified quotes with realistic volatility
            modified_quotes = self._create_monte_carlo_quotes(volatility_multiplier)

            # Execute backtest
            result = executor.execute(
                modified_quotes, base_strategy, strategy_name=f'Monte Carlo Simulation {sim_num+1}'
            )

            # Convert to dictionary
            initial_capital = float(self.backtest_config.initial_capital)
            final_capital = float(result.final_capital)

            result_dict = {
                'test_type': 'monte_carlo',
                'test_name': f'Monte Carlo - Simulation {sim_num+1}',
                'simulation_num': sim_num + 1,
                'volatility_multiplier': volatility_multiplier,
                'modules_active': list(self.raw_config['modules']['filters'].keys()),
                'learning_engine': None,
                'thresholds': thresholds_helper(strategy_config),
                'total_pnl': final_capital - initial_capital,
                'return_pct': (
                    ((final_capital - initial_capital) / initial_capital * 100)
                    if initial_capital > 0
                    else 0.0
                ),
                'win_rate': float(result.performance.win_rate) if result.performance else 0.0,
                'sharpe_ratio': (
                    float(result.performance.sharpe_ratio)
                    if result.performance and result.performance.sharpe_ratio
                    else 0.0
                ),
                'max_drawdown': (
                    float(result.performance.max_drawdown_percentage) if result.performance else 0.0
                ),
                'total_trades': result.performance.total_trades if result.performance else 0,
                'avg_trade_pnl': (
                    (final_capital - initial_capital) / result.performance.total_trades
                    if result.performance and result.performance.total_trades > 0
                    else 0.0
                ),
                'final_capital': final_capital,
            }

            results.append(result_dict)
            self.memory_manager.add_result(result_dict)

        logger.info(f"Monte Carlo completed: {len(results)} simulations")

        return results

    def _create_monte_carlo_quotes(self, volatility_multiplier: float) -> List:
        """
        Create quotes modified with realistic volatility for Monte Carlo.

        Uses RealisticDataGenerator with GARCH and regime switching.

        Args:
            volatility_multiplier: Volatility multiplier

        Returns:
            List of modified quotes with realistic data
        """
        from app.backtesting.realistic_data_generator import RealisticDataGenerator

        # If no base quotes, create new realistic data
        if not self.quotes:
            logger.warning("No base quotes available, generating new realistic data")
            gen = RealisticDataGenerator(
                seed=self.raw_config.get('random_state', 42),
                base_price=100.0,
                base_volume=50_000_000,
            )

            start_date = datetime.now()
            return gen.generate_realistic_quotes(
                symbol='SYNTH',
                n_days=252,
                start_date=start_date,
                use_regime_switching=True,
            )

        # Use realistic generator for Monte Carlo simulations
        gen = RealisticDataGenerator(
            seed=self.raw_config.get('random_state', 42),
            base_price=float(self.quotes[0].close),
            base_volume=int(self.quotes[0].volume) if self.quotes[0].volume else 50_000_000,
        )

        start_date = self.quotes[0].timestamp if self.quotes else datetime.now()

        modified_quotes = gen.generate_realistic_quotes(
            symbol=self.quotes[0].symbol if self.quotes else 'SYNTH',
            n_days=len(self.quotes),
            start_date=start_date,
            use_regime_switching=True,
            initial_regime='volatile',  # Use volatile regime for Monte Carlo
        )

        logger.info(
            f"Generated {len(modified_quotes)} realistic Monte Carlo quotes "
            f"(replacing simplistic random shocks)"
        )

        return modified_quotes

    def run_walk_forward_backtest(
        self,
        create_strategy_config_helper,
        thresholds_helper,
        strategy_name_helper,
        metrics_helper,
        audit_helper,
    ) -> List[Dict[str, Any]]:
        """
        Execute walk-forward backtest with rolling windows.

        Implements validation following:
        - Ruey Tsay (Analysis of Financial Time Series)
        - Lopez de Prado (Advances in Financial Machine Learning)

        Architecture:
        - Divides data into rolling windows (train/test)
        - Default: 70% train, 30% test per window
        - Minimum training period: 100 days
        - Step size: 63 days (quarterly)

        Returns:
            List of results with aggregated metrics across windows
        """
        logger.info("Running walk-forward backtest...")

        wf_config = self.raw_config.get('backtests', {}).get('walk_forward', {})

        # Window parameters with defaults
        train_pct = wf_config.get('train_pct', 0.70)
        test_pct = wf_config.get('test_pct', 0.30)
        min_train_days = wf_config.get('min_train_days', 100)
        step_size_days = wf_config.get('step_size_days', 63)

        logger.info(
            f"Walk-forward config: train={train_pct:.0%}, test={test_pct:.0%}, "
            f"min_train={min_train_days}d, step={step_size_days}d"
        )

        # Sort quotes by timestamp (temporal order is critical)
        sorted_quotes = sorted(self.quotes, key=lambda x: x.timestamp)
        total_days = len(sorted_quotes)

        logger.info(
            f"Total data: {total_days} days from {sorted_quotes[0].timestamp.date()} "
            f"to {sorted_quotes[-1].timestamp.date()}"
        )

        # Create walk-forward windows
        window_size = math.ceil(min_train_days / train_pct)

        num_windows = 0
        windows = []

        start_idx = 0
        while True:
            end_idx = start_idx + window_size

            if end_idx > total_days:
                break

            window_quotes = sorted_quotes[start_idx:end_idx]

            train_size = math.ceil(len(window_quotes) * train_pct)
            if train_size < min_train_days:
                logger.warning(
                    f"Window {num_windows+1}: Insufficient training data "
                    f"({train_size} < {min_train_days})"
                )
                start_idx += step_size_days
                continue

            train_quotes = window_quotes[:train_size]
            test_quotes = window_quotes[train_size:]

            windows.append(
                {
                    'window_num': num_windows + 1,
                    'train': train_quotes,
                    'test': test_quotes,
                    'train_start': train_quotes[0].timestamp,
                    'train_end': train_quotes[-1].timestamp,
                    'test_start': test_quotes[0].timestamp,
                    'test_end': test_quotes[-1].timestamp,
                }
            )

            num_windows += 1
            start_idx += step_size_days

        if not windows:
            logger.error("No valid walk-forward windows created")
            return []

        logger.info(f"Created {num_windows} walk-forward windows")

        # Execute backtest for each window
        window_results = []

        for window in windows:
            logger.info(
                f"\nWindow {window['window_num']}/{num_windows}: "
                f"Train: {window['train_start'].date()} to {window['train_end'].date()} "
                f"({len(window['train'])} days) | "
                f"Test: {window['test_start'].date()} to {window['test_end'].date()} "
                f"({len(window['test'])} days)"
            )

            try:
                strategy_config = create_strategy_config_helper()
                strategy = ModularMomentumStrategy(strategy_config)

                train_quotes = window['train']
                test_quotes = window['test']

                # Execute backtest on test period only
                initial_capital = self.backtest_config.initial_capital
                backtest_config = BacktestConfig(
                    initial_capital=initial_capital,
                    commission_per_trade=self.backtest_config.commission_per_trade,
                    slippage_percentage=self.backtest_config.slippage_percentage,
                    max_position_size=self.backtest_config.max_position_size,
                    stop_loss_percentage=self.backtest_config.stop_loss_percentage,
                    take_profit_percentage=self.backtest_config.take_profit_percentage,
                    risk_free_rate=self.backtest_config.risk_free_rate,
                )

                strategy_name = strategy_name_helper(strategy)
                executor = SimpleBacktestExecutor(backtest_config)

                result = executor.execute(
                    test_quotes,
                    strategy,
                    strategy_name=f"{strategy_name}_WF_Window{window['window_num']}",
                )

                consistent_metrics = metrics_helper(result, initial_capital)

                window_result = {
                    'window_num': window['window_num'],
                    'train_start': window['train_start'],
                    'train_end': window['train_end'],
                    'test_start': window['test_start'],
                    'test_end': window['test_end'],
                    'train_size': len(train_quotes),
                    'test_size': len(test_quotes),
                    'total_pnl': consistent_metrics['total_pnl'],
                    'return_pct': consistent_metrics['return_pct'],
                    'win_rate': float(result.performance.win_rate) if result.performance else 0.0,
                    'sharpe_ratio': (
                        float(result.performance.sharpe_ratio)
                        if result.performance and result.performance.sharpe_ratio
                        else 0.0
                    ),
                    'max_drawdown': (
                        float(result.performance.max_drawdown_percentage)
                        if result.performance
                        else 0.0
                    ),
                    'total_trades': result.performance.total_trades if result.performance else 0,
                    'final_capital': consistent_metrics['final_capital'],
                    'avg_trade_pnl': (
                        consistent_metrics['total_pnl'] / result.performance.total_trades
                        if result.performance and result.performance.total_trades > 0
                        else 0.0
                    ),
                }

                window_results.append(window_result)

                logger.info(
                    f"Window {window['window_num']} result: "
                    f"Return={window_result['return_pct']:.2f}%, "
                    f"Sharpe={window_result['sharpe_ratio']:.2f}, "
                    f"Trades={window_result['total_trades']}"
                )

                self.memory_manager.add_backtest_object(
                    f'walk_forward_window_{window["window_num"]}', result
                )

            except Exception as e:
                logger.error(f"Error in window {window['window_num']}: {e}", exc_info=True)
                continue

        if not window_results:
            logger.error("No windows completed successfully")
            return []

        # Aggregate results across windows
        sharpe_values = [w['sharpe_ratio'] for w in window_results]
        return_values = [w['return_pct'] for w in window_results]
        drawdown_values = [w['max_drawdown'] for w in window_results]

        avg_sharpe = np.mean(sharpe_values)
        std_sharpe = np.std(sharpe_values)
        avg_return = np.mean(return_values)
        std_return = np.std(return_values)
        avg_drawdown = np.mean(drawdown_values)

        # Stability ratio (signal-to-noise)
        stability_ratio = avg_sharpe / (std_sharpe + 1e-6)

        # Create consolidated result
        consolidated_result = {
            'test_type': 'walk_forward',
            'test_name': 'Walk-Forward Validation',
            'num_windows': num_windows,
            'window_metrics': window_results,
            'avg_sharpe': avg_sharpe,
            'sharpe_std': std_sharpe,
            'avg_return': avg_return,
            'return_std': std_return,
            'avg_max_drawdown': avg_drawdown,
            'stability_ratio': stability_ratio,
            'train_pct': train_pct,
            'test_pct': test_pct,
            'min_train_days': min_train_days,
            'step_size_days': step_size_days,
            'sharpe_min': np.min(sharpe_values),
            'sharpe_max': np.max(sharpe_values),
            'return_min': np.min(return_values),
            'return_max': np.max(return_values),
            'win_rate': np.mean([w['win_rate'] for w in window_results]),
            'total_trades': np.sum([w['total_trades'] for w in window_results]),
            'modules_active': list(self.raw_config['modules']['filters'].keys()),
            'learning_engine': None,
            'thresholds': thresholds_helper(create_strategy_config_helper()),
        }

        # Log summary
        logger.info("\n" + "=" * 80)
        logger.info("WALK-FORWARD VALIDATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Windows tested: {num_windows}")
        logger.info("Performance (mean +/- std):")
        logger.info(
            f"  Sharpe: {avg_sharpe:.3f} +/- {std_sharpe:.3f} (range: {consolidated_result['sharpe_min']:.2f} to {consolidated_result['sharpe_max']:.2f})"
        )
        logger.info(
            f"  Return: {avg_return:.2f}% +/- {std_return:.2f}% (range: {consolidated_result['return_min']:.2f}% to {consolidated_result['return_max']:.2f}%)"
        )
        logger.info(f"  Max DD: {avg_drawdown:.2f}%")
        logger.info(f"Stability ratio (signal/noise): {stability_ratio:.2f}")
        logger.info(f"Win rate: {consolidated_result['win_rate']:.1%}")
        logger.info(f"Total trades: {consolidated_result['total_trades']}")
        logger.info("=" * 80)

        self.memory_manager.add_result(consolidated_result)
        audit_helper(consolidated_result, 'walk_forward', strategy)

        return [consolidated_result]

    def run_backtest_with_quotes(
        self,
        strategy: ModularMomentumStrategy,
        quotes: List,
        initial_capital: Decimal,
        strategy_name_helper,
    ) -> Any:
        """
        Run backtest with specific quotes.

        Args:
            strategy: Strategy to backtest
            quotes: Quotes to use
            initial_capital: Initial capital
            strategy_name_helper: Helper function to get strategy name

        Returns:
            BacktestResult
        """
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=self.backtest_config.commission_per_trade,
            slippage_percentage=self.backtest_config.slippage_percentage,
            max_position_size=self.backtest_config.max_position_size,
            stop_loss_percentage=self.backtest_config.stop_loss_percentage,
            take_profit_percentage=self.backtest_config.take_profit_percentage,
            risk_free_rate=self.backtest_config.risk_free_rate,
        )

        strategy_name = strategy_name_helper(strategy)
        executor = SimpleBacktestExecutor(backtest_config)
        result = executor.execute(quotes, strategy, strategy_name=strategy_name)

        return result
