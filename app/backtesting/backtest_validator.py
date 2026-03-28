"""
Backtest Validator Module - Validation logic for backtests.

Extracted from comprehensive_backtest_runner.py for Single Responsibility.
Handles validation of backtest results:
- Out-of-sample validation
- Compliance validation (R5, R6, R7, DATA-001)
- Performance degradation analysis
- Stationarity tests (ADF)
- Triple barrier labeling
- Meta-labeling

Architecture:
- Implements Lopez de Prado and Tsay validation rules
- Proper train/test splits without look-ahead bias
- Concept drift detection
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from app.backtesting.backtesting_compliance import (
    BacktestingComplianceResult,
    create_backtesting_compliance,
)
from app.backtesting.core.error_handling import train_with_retry
from app.backtesting.core.executor import SimpleBacktestExecutor
from app.backtesting.core.memory_manager import AggressiveMemoryManager
from app.backtesting.models import BacktestConfig
from app.domain.strategies.momentum_modular.strategy import ModularMomentumStrategy


class BacktestValidator:
    """
    Handles validation logic for backtests.

    Provides methods for:
    - Out-of-sample validation
    - Compliance validation (R5, R6, R7, DATA-001)
    - Performance degradation analysis
    - Stationarity tests
    - Triple barrier labeling
    - Meta-labeling
    """

    def __init__(
        self,
        backtest_config: BacktestConfig,
        memory_manager: AggressiveMemoryManager,
        raw_config: Dict[str, Any],
        quotes: List,
    ):
        """
        Initialize BacktestValidator.

        Args:
            backtest_config: Backtest configuration
            memory_manager: Memory manager for storing results
            raw_config: Raw YAML configuration
            quotes: Loaded market data quotes
        """
        self.backtest_config = backtest_config
        self.memory_manager = memory_manager
        self.raw_config = raw_config
        self.quotes = quotes

        # Initialize BacktestingCompliance for R5, R6, R7, DATA-001
        self.backtesting_compliance = create_backtesting_compliance()
        self.compliance_results: List[BacktestingComplianceResult] = []

    # =========================================================================
    # Out-of-Sample Backtest - Main Entry Point
    # =========================================================================

    def run_out_of_sample_backtest(
        self,
        create_strategy_config_helper,
        strategy_name_helper,
        metrics_helper,
        audit_helper,
        thresholds_helper,
    ) -> List[Dict[str, Any]]:
        """
        Execute out-of-sample backtest with rigorous validation.

        Implements rules from Lopez de Prado and Tsay:
        - NO peeking at OOS data during training
        - Triple Barrier labeling for realistic evaluation
        - ADF test for stationarity in both periods
        - Detection of concept drift and performance degradation

        Architecture:
        - 70% In-Sample (training): start_date -> split_date
        - 30% Out-of-Sample (validation): split_date+1 -> end_date
        - Parameters FROZEN during OOS (no re-training)

        Returns:
            List with OOS test result including metrics and validation flags
        """
        from app.shared.performance.statsmodels_fallback import adfuller

        logger.info("=" * 80)
        logger.info("OUT-OF-SAMPLE BACKTEST - Starting rigorous validation")
        logger.info("=" * 80)

        # Load and validate configuration
        oos_config = self._load_oos_config()
        train_ratio = oos_config.get('train_ratio', 0.70)
        acceptable_degradation = oos_config.get('acceptable_degradation_pct', 0.30)
        concept_drift_threshold = oos_config.get('concept_drift_threshold', 0.50)

        logger.info(f"OOS Configuration: {train_ratio:.0%} train, {1-train_ratio:.0%} test")
        logger.info(f"Acceptable degradation: {acceptable_degradation:.0%}")
        logger.info(f"Concept drift threshold: {concept_drift_threshold:.0%}")

        # Split data into in-sample and out-of-sample
        split_result = self._split_data_for_oos(oos_config, train_ratio)
        if not split_result:
            return []

        in_sample_quotes, out_of_sample_quotes = split_result

        # Run stationarity tests
        in_sample_prices = pd.Series([float(q.close) for q in in_sample_quotes])
        oos_prices = pd.Series([float(q.close) for q in out_of_sample_quotes])
        stationarity_test = self._run_stationarity_tests(in_sample_prices, oos_prices, adfuller)

        # Train strategy on in-sample data
        strategy_config = create_strategy_config_helper()
        strategy, learning_engine_used = self._train_strategy_on_in_sample(strategy_config)

        # Execute in-sample backtest
        in_sample_result, in_sample_metrics = self._execute_in_sample_backtest(
            in_sample_quotes, strategy, strategy_name_helper, metrics_helper
        )

        # Execute out-of-sample backtest
        oos_result, oos_metrics = self._execute_oos_backtest(
            out_of_sample_quotes, strategy_config, strategy_name_helper, metrics_helper
        )

        # Analyze performance degradation
        degradation_analysis = self._analyze_performance_degradation(
            in_sample_metrics,
            oos_metrics,
            in_sample_result,
            oos_result,
            acceptable_degradation,
            concept_drift_threshold,
        )

        # Run volatility regime analysis
        in_sample_returns = in_sample_prices.pct_change().dropna()
        oos_returns = oos_prices.pct_change().dropna()
        volatility_analysis = self._analyze_volatility_regime(in_sample_returns, oos_returns)

        # Triple barrier validation
        triple_barrier = self._run_triple_barrier_validation(in_sample_prices, oos_prices)

        # Build and return comprehensive result
        result_dict = self._build_oos_result_dict(
            in_sample_quotes,
            out_of_sample_quotes,
            in_sample_result,
            in_sample_metrics,
            oos_result,
            oos_metrics,
            degradation_analysis,
            volatility_analysis,
            stationarity_test,
            triple_barrier,
            learning_engine_used,
            strategy_config,
            strategy,
            thresholds_helper,
        )

        self.memory_manager.add_result(result_dict)
        self.memory_manager.add_backtest_object('out_of_sample', oos_result)
        audit_helper(result_dict, 'out_of_sample', strategy)

        self._log_oos_completion(result_dict, degradation_analysis, acceptable_degradation)

        return [result_dict]

    # =========================================================================
    # Out-of-Sample Backtest - Helper Methods
    # =========================================================================

    def _load_oos_config(self) -> Dict[str, Any]:
        """Load out-of-sample test configuration."""
        return self.raw_config.get('backtests', {}).get('out_of_sample', {})

    def _split_data_for_oos(
        self, oos_config: Dict[str, Any], train_ratio: float
    ) -> Optional[tuple]:
        """
        Split quotes into in-sample and out-of-sample periods.

        Returns:
            Tuple of (in_sample_quotes, out_of_sample_quotes) or None if insufficient data.
        """
        all_quotes = sorted(self.quotes, key=lambda x: x.timestamp)
        start_date = all_quotes[0].timestamp
        end_date = all_quotes[-1].timestamp
        total_period = (end_date - start_date).days

        logger.info(f"Full dataset: {start_date.date()} to {end_date.date()} ({total_period} days)")

        split_delta = timedelta(days=int(total_period * train_ratio))
        split_date = start_date + split_delta
        logger.info(f"Split point: {split_date.date()}")

        in_sample_quotes = [q for q in all_quotes if q.timestamp <= split_date]
        out_of_sample_quotes = [q for q in all_quotes if q.timestamp > split_date]

        min_test_size = oos_config.get('min_test_size', 100)
        min_train_size = oos_config.get('min_train_size', 100)

        if len(in_sample_quotes) < min_train_size or len(out_of_sample_quotes) < min_test_size:
            logger.error(
                f"Insufficient data for OOS test: "
                f"in-sample={len(in_sample_quotes)} (min {min_train_size}), "
                f"out-of-sample={len(out_of_sample_quotes)} (min {min_test_size})"
            )
            return None

        logger.info("Data split:")
        logger.info(
            f"  In-Sample (training):   {len(in_sample_quotes):5d} quotes "
            f"({in_sample_quotes[0].timestamp.date()} -> {in_sample_quotes[-1].timestamp.date()})"
        )
        logger.info(
            f"  Out-of-Sample (testing): {len(out_of_sample_quotes):5d} quotes "
            f"({out_of_sample_quotes[0].timestamp.date()} -> {out_of_sample_quotes[-1].timestamp.date()})"
        )

        return in_sample_quotes, out_of_sample_quotes

    def _run_stationarity_tests(
        self, in_sample_prices: pd.Series, oos_prices: pd.Series, adfuller_func
    ) -> Dict[str, Any]:
        """Run ADF stationarity tests on both sample period returns."""
        logger.info("\n" + "-" * 80)
        logger.info("STATIONARITY TESTS (Augmented Dickey-Fuller)")
        logger.info("-" * 80)

        in_sample_returns = in_sample_prices.pct_change().dropna()
        oos_returns = oos_prices.pct_change().dropna()

        adf_in_sample = adfuller_func(in_sample_returns, regression='c')
        is_in_sample_stationary = adf_in_sample[1] < 0.05

        logger.info("In-Sample Returns:")
        logger.info(f"  ADF Statistic: {adf_in_sample[0]:.4f}")
        logger.info(f"  p-value:       {adf_in_sample[1]:.4f}")
        logger.info(f"  Stationary:    {is_in_sample_stationary}")

        adf_oos = adfuller_func(oos_returns, regression='c')
        is_oos_stationary = adf_oos[1] < 0.05

        logger.info("Out-of-Sample Returns:")
        logger.info(f"  ADF Statistic: {adf_oos[0]:.4f}")
        logger.info(f"  p-value:       {adf_oos[1]:.4f}")
        logger.info(f"  Stationary:    {is_oos_stationary}")

        if is_in_sample_stationary and is_oos_stationary:
            recommendation = 'Suitable for mean reversion'
        elif not is_in_sample_stationary:
            recommendation = 'Use returns instead of prices'
        else:
            recommendation = 'Regime change detected - proceed with caution'

        logger.info(f"\nRecommendation: {recommendation}")

        return {
            'in_sample': {
                'adf_statistic': float(adf_in_sample[0]),
                'p_value': float(adf_in_sample[1]),
                'is_stationary': is_in_sample_stationary,
            },
            'out_of_sample': {
                'adf_statistic': float(adf_oos[0]),
                'p_value': float(adf_oos[1]),
                'is_stationary': is_oos_stationary,
            },
            'both_stationary': is_in_sample_stationary and is_oos_stationary,
            'recommendation': recommendation,
        }

    def _train_strategy_on_in_sample(self, strategy_config: Dict[str, Any]) -> tuple:
        """
        Train strategy on in-sample data only.

        Returns:
            Tuple of (strategy, learning_engine_used).
        """
        logger.info("\n" + "-" * 80)
        logger.info("TRAINING PHASE (In-Sample Only)")
        logger.info("-" * 80)
        logger.info("Training strategy on in-sample data...")

        strategy = ModularMomentumStrategy(strategy_config)
        learning_engine_used = None

        if hasattr(strategy, 'learning_engine') and strategy.learning_engine:
            try:
                training_success = train_with_retry(
                    strategy=strategy, engine_type='supervised', use_subprocess=False
                )
                if training_success:
                    learning_engine_used = 'supervised'
                    logger.info("Learning engine trained successfully on in-sample data")
                else:
                    logger.warning("Learning engine training failed, using untrained strategy")
            except Exception as e:
                logger.warning(f"Learning engine training error: {e}")

        return strategy, learning_engine_used

    def _execute_in_sample_backtest(
        self,
        in_sample_quotes: List,
        strategy,
        strategy_name_helper,
        metrics_helper,
    ) -> tuple:
        """Execute backtest on in-sample data for baseline metrics."""
        logger.info("\nRunning in-sample backtest...")

        initial_capital = self.backtest_config.initial_capital
        backtest_config = self._create_backtest_config()
        strategy_name = strategy_name_helper(strategy)
        executor = SimpleBacktestExecutor(backtest_config)

        in_sample_result = executor.execute(
            in_sample_quotes, strategy, strategy_name=f"{strategy_name}_IS"
        )
        in_sample_metrics = metrics_helper(in_sample_result, initial_capital)

        logger.info("In-Sample Results:")
        logger.info(f"  Return:       {in_sample_metrics['return_pct']:.2f}%")
        logger.info(f"  Sharpe:       {float(in_sample_result.performance.sharpe_ratio or 0):.3f}")
        logger.info(f"  Win Rate:     {float(in_sample_result.performance.win_rate):.2%}")
        logger.info(
            f"  Max DD:       {float(in_sample_result.performance.max_drawdown_percentage):.2%}"
        )
        logger.info(f"  Total Trades: {in_sample_result.performance.total_trades}")

        return in_sample_result, in_sample_metrics

    def _execute_oos_backtest(
        self,
        out_of_sample_quotes: List,
        strategy_config: Dict[str, Any],
        strategy_name_helper,
        metrics_helper,
    ) -> tuple:
        """Execute out-of-sample backtest with frozen parameters."""
        logger.info("\n" + "-" * 80)
        logger.info("VALIDATION PHASE (Out-of-Sample - Frozen Parameters)")
        logger.info("-" * 80)
        logger.info("Running out-of-sample backtest with FROZEN parameters...")

        initial_capital = self.backtest_config.initial_capital
        oos_strategy = ModularMomentumStrategy(strategy_config)
        backtest_config = self._create_backtest_config()
        strategy_name = strategy_name_helper(oos_strategy)
        executor = SimpleBacktestExecutor(backtest_config)

        oos_result = executor.execute(
            out_of_sample_quotes, oos_strategy, strategy_name=f"{strategy_name}_OOS"
        )
        oos_metrics = metrics_helper(oos_result, initial_capital)

        logger.info("Out-of-Sample Results:")
        logger.info(f"  Return:       {oos_metrics['return_pct']:.2f}%")
        logger.info(f"  Sharpe:       {float(oos_result.performance.sharpe_ratio or 0):.3f}")
        logger.info(f"  Win Rate:     {float(oos_result.performance.win_rate):.2%}")
        logger.info(f"  Max DD:       {float(oos_result.performance.max_drawdown_percentage):.2%}")
        logger.info(f"  Total Trades: {oos_result.performance.total_trades}")

        return oos_result, oos_metrics

    def _create_backtest_config(self) -> BacktestConfig:
        """Create BacktestConfig from instance configuration."""
        return BacktestConfig(
            initial_capital=self.backtest_config.initial_capital,
            commission_per_trade=self.backtest_config.commission_per_trade,
            slippage_percentage=self.backtest_config.slippage_percentage,
            max_position_size=self.backtest_config.max_position_size,
            stop_loss_percentage=self.backtest_config.stop_loss_percentage,
            take_profit_percentage=self.backtest_config.take_profit_percentage,
            risk_free_rate=self.backtest_config.risk_free_rate,
        )

    def _calculate_percentage_drop(self, is_value: float, oos_value: float) -> float:
        """Calculate percentage drop from in-sample to out-of-sample."""
        if is_value != 0:
            return (is_value - oos_value) / abs(is_value) * 100
        return 0 if oos_value == 0 else -100

    def _analyze_performance_degradation(
        self,
        in_sample_metrics: Dict,
        oos_metrics: Dict,
        in_sample_result,
        oos_result,
        acceptable_degradation: float,
        concept_drift_threshold: float,
    ) -> Dict[str, Any]:
        """Analyze performance degradation between in-sample and out-of-sample."""
        logger.info("\n" + "-" * 80)
        logger.info("PERFORMANCE DEGRADATION ANALYSIS")
        logger.info("-" * 80)

        is_return = in_sample_metrics['return_pct']
        oos_return = oos_metrics['return_pct']
        is_sharpe = float(in_sample_result.performance.sharpe_ratio or 0)
        oos_sharpe = float(oos_result.performance.sharpe_ratio or 0)
        is_win_rate = float(in_sample_result.performance.win_rate)
        oos_win_rate = float(oos_result.performance.win_rate)
        is_max_dd = float(in_sample_result.performance.max_drawdown_percentage)
        oos_max_dd = float(oos_result.performance.max_drawdown_percentage)

        return_drop = self._calculate_percentage_drop(is_return, oos_return)
        sharpe_drop = self._calculate_percentage_drop(is_sharpe, oos_sharpe)
        win_rate_drop = self._calculate_percentage_drop(is_win_rate, oos_win_rate)

        # Concept drift detection
        if is_return > 0:
            concept_drift_detected = oos_return < concept_drift_threshold * is_return
        else:
            concept_drift_detected = oos_return < is_return

        is_acceptable = sharpe_drop < (acceptable_degradation * 100)

        self._log_degradation_analysis(
            is_return,
            oos_return,
            return_drop,
            is_sharpe,
            oos_sharpe,
            sharpe_drop,
            is_win_rate,
            oos_win_rate,
            win_rate_drop,
            is_max_dd,
            oos_max_dd,
            concept_drift_detected,
            is_acceptable,
        )

        return {
            'return_drop_pct': float(return_drop),
            'sharpe_drop_pct': float(sharpe_drop),
            'win_rate_drop_pct': float(win_rate_drop),
            'max_dd_change_pct': float(oos_max_dd - is_max_dd),
            'is_acceptable': bool(is_acceptable),
            'acceptable_threshold': float(acceptable_degradation * 100),
            'concept_drift_detected': bool(concept_drift_detected),
            'is_return': is_return,
            'oos_return': oos_return,
            'is_sharpe': is_sharpe,
            'oos_sharpe': oos_sharpe,
            'is_win_rate': is_win_rate,
            'oos_win_rate': oos_win_rate,
            'is_max_dd': is_max_dd,
            'oos_max_dd': oos_max_dd,
        }

    def _log_degradation_analysis(
        self,
        is_return,
        oos_return,
        return_drop,
        is_sharpe,
        oos_sharpe,
        sharpe_drop,
        is_win_rate,
        oos_win_rate,
        win_rate_drop,
        is_max_dd,
        oos_max_dd,
        concept_drift_detected,
        is_acceptable,
    ):
        """Log degradation analysis results."""
        logger.info("Return Degradation:")
        logger.info(f"  In-Sample:     {is_return:+.2f}%")
        logger.info(f"  Out-of-Sample: {oos_return:+.2f}%")
        logger.info(f"  Drop:           {return_drop:+.1f}%")

        logger.info("Sharpe Ratio Degradation:")
        logger.info(f"  In-Sample:     {is_sharpe:.3f}")
        logger.info(f"  Out-of-Sample: {oos_sharpe:.3f}")
        logger.info(f"  Drop:           {sharpe_drop:+.1f}%")

        logger.info("Win Rate Change:")
        logger.info(f"  In-Sample:     {is_win_rate:.2%}")
        logger.info(f"  Out-of-Sample: {oos_win_rate:.2%}")
        logger.info(f"  Drop:           {win_rate_drop:+.1f}%")

        logger.info("Max Drawdown Comparison:")
        logger.info(f"  In-Sample:     {is_max_dd:.2%}%")
        logger.info(f"  Out-of-Sample: {oos_max_dd:.2%}%")
        logger.info(f"  Change:         {oos_max_dd - is_max_dd:+.2f}%")

        logger.info("\nValidation Summary:")
        logger.info(f"  Concept Drift Detected: {concept_drift_detected}")
        logger.info(f"  Degradation Acceptable:  {is_acceptable}")
        logger.info(f"  Overall Status:          {'PASS' if is_acceptable else 'FAIL'}")

    def _analyze_volatility_regime(
        self, in_sample_returns: pd.Series, oos_returns: pd.Series
    ) -> Dict[str, Any]:
        """Analyze volatility regime changes between periods."""
        in_vol = float(in_sample_returns.std() * np.sqrt(252))
        oos_vol = float(oos_returns.std() * np.sqrt(252))
        vol_regime_change = abs(oos_vol - in_vol) / in_vol > 0.20 if in_vol > 0 else False

        logger.info("Volatility Regime:")
        logger.info(f"  In-Sample:     {in_vol:.2%}")
        logger.info(f"  Out-of-Sample: {oos_vol:.2%}")
        logger.info(f"  Regime Change:  {vol_regime_change}")

        return {
            'in_sample_annualized': in_vol,
            'oos_annualized': oos_vol,
            'regime_change_detected': vol_regime_change,
            'vol_change_pct': float((oos_vol - in_vol) / in_vol * 100) if in_vol > 0 else 0.0,
        }

    def _run_triple_barrier_validation(
        self, in_sample_prices: pd.Series, oos_prices: pd.Series
    ) -> Dict[str, Any]:
        """Run triple barrier labeling validation."""
        logger.info("\n" + "-" * 80)
        logger.info("TRIPLE BARRIER LABELING VALIDATION")
        logger.info("-" * 80)

        in_labels = self._triple_barrier_labels(in_sample_prices)
        oos_labels = self._triple_barrier_labels(oos_prices)

        in_signal_quality = np.mean([1 for lbl in in_labels if lbl == 1]) if in_labels else 0
        oos_signal_quality = np.mean([1 for lbl in oos_labels if lbl == 1]) if oos_labels else 0

        logger.info("Signal Quality (Triple Barrier):")
        logger.info(f"  In-Sample:     {in_signal_quality:.2%} positive labels")
        logger.info(f"  Out-of-Sample: {oos_signal_quality:.2%} positive labels")
        logger.info(f"  Degradation:   {(in_signal_quality - oos_signal_quality) * 100:+.1f}%")

        return {
            'in_sample_signal_quality': float(in_signal_quality),
            'oos_signal_quality': float(oos_signal_quality),
            'quality_degradation_pct': float((in_signal_quality - oos_signal_quality) * 100),
        }

    def _build_oos_result_dict(
        self,
        in_sample_quotes,
        out_of_sample_quotes,
        in_sample_result,
        in_sample_metrics,
        oos_result,
        oos_metrics,
        degradation_analysis,
        volatility_analysis,
        stationarity_test,
        triple_barrier,
        learning_engine_used,
        strategy_config,
        strategy,
        thresholds_helper,
    ) -> Dict[str, Any]:
        """Build comprehensive result dictionary for OOS test."""
        is_acceptable = degradation_analysis['is_acceptable']
        concept_drift_detected = degradation_analysis['concept_drift_detected']

        return {
            'test_type': 'out_of_sample',
            'test_name': 'Out-of-Sample Validation',
            'in_sample_period': {
                'start': in_sample_quotes[0].timestamp.date().isoformat(),
                'end': in_sample_quotes[-1].timestamp.date().isoformat(),
                'n_quotes': len(in_sample_quotes),
            },
            'out_of_sample_period': {
                'start': out_of_sample_quotes[0].timestamp.date().isoformat(),
                'end': out_of_sample_quotes[-1].timestamp.date().isoformat(),
                'n_quotes': len(out_of_sample_quotes),
            },
            'in_sample_metrics': {
                'return': degradation_analysis['is_return'],
                'sharpe': degradation_analysis['is_sharpe'],
                'win_rate': degradation_analysis['is_win_rate'],
                'max_dd': degradation_analysis['is_max_dd'],
                'total_trades': in_sample_result.performance.total_trades,
                'total_pnl': float(in_sample_metrics['total_pnl']),
                'final_capital': float(in_sample_metrics['final_capital']),
            },
            'out_of_sample_metrics': {
                'return': degradation_analysis['oos_return'],
                'sharpe': degradation_analysis['oos_sharpe'],
                'win_rate': degradation_analysis['oos_win_rate'],
                'max_dd': degradation_analysis['oos_max_dd'],
                'total_trades': oos_result.performance.total_trades,
                'total_pnl': float(oos_metrics['total_pnl']),
                'final_capital': float(oos_metrics['final_capital']),
            },
            'performance_degradation': {
                'return_drop_pct': degradation_analysis['return_drop_pct'],
                'sharpe_drop_pct': degradation_analysis['sharpe_drop_pct'],
                'win_rate_drop_pct': degradation_analysis['win_rate_drop_pct'],
                'max_dd_change_pct': degradation_analysis['max_dd_change_pct'],
                'is_acceptable': is_acceptable,
                'acceptable_threshold': degradation_analysis['acceptable_threshold'],
            },
            'concept_drift': {
                'detected': concept_drift_detected,
                'threshold': float(self._load_oos_config().get('concept_drift_threshold', 0.50)),
                'in_sample_return': degradation_analysis['is_return'],
                'oos_return': degradation_analysis['oos_return'],
                'return_ratio': (
                    degradation_analysis['oos_return'] / degradation_analysis['is_return']
                    if degradation_analysis['is_return'] != 0
                    else 0.0
                ),
            },
            'volatility_regime': volatility_analysis,
            'stationarity_test': stationarity_test,
            'triple_barrier': triple_barrier,
            'learning_engine_used': learning_engine_used,
            'frozen_parameters': True,
            'validation_passed': bool(is_acceptable and not concept_drift_detected),
            'overall_status': 'PASS' if (is_acceptable and not concept_drift_detected) else 'FAIL',
            'modules_active': (
                list(self.raw_config['modules']['filters'].keys())
                if 'modules' in self.raw_config
                else []
            ),
            'thresholds': thresholds_helper(strategy_config),
        }

    def _log_oos_completion(
        self, result_dict: Dict, degradation_analysis: Dict, acceptable_degradation: float
    ):
        """Log OOS backtest completion summary."""
        logger.info("\n" + "=" * 80)
        logger.info("OUT-OF-SAMPLE BACKTEST COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Overall Status: {result_dict['overall_status']}")
        logger.info(f"Validation Passed: {result_dict['validation_passed']}")
        detected = 'DETECTED' if degradation_analysis['concept_drift_detected'] else 'NOT DETECTED'
        logger.info(f"Concept Drift: {detected}")
        logger.info(
            f"Degradation: {degradation_analysis['sharpe_drop_pct']:.1f}% "
            f"(threshold: {acceptable_degradation*100:.0f}%)"
        )
        logger.info("=" * 80)

    # =========================================================================
    # Triple Barrier Labeling
    # =========================================================================

    def _triple_barrier_labels(
        self,
        prices: pd.Series,
        target_return: float = 0.02,
        stop_loss: float = 0.01,
        max_holding: int = 20,
    ) -> List[int]:
        """
        Apply triple barrier labeling (Lopez de Prado).

        Args:
            prices: Price series
            target_return: Target return for upper barrier
            stop_loss: Stop loss for lower barrier
            max_holding: Maximum holding period

        Returns:
            List of labels (1=target hit, -1=stop loss, 0=timeout)
        """
        labels = []
        for i in range(len(prices) - max_holding):
            entry_price = prices.iloc[i]
            upper_barrier = entry_price * (1 + target_return)
            lower_barrier = entry_price * (1 - stop_loss)

            label = 0  # Timeout
            for j in range(i + 1, min(i + max_holding, len(prices))):
                price = prices.iloc[j]
                if price >= upper_barrier:
                    label = 1  # Hit target
                    break
                elif price <= lower_barrier:
                    label = -1  # Hit stop loss
                    break

                # Check final return on timeout
                if j == min(i + max_holding, len(prices)) - 1:
                    final_return = (prices.iloc[j] - entry_price) / entry_price
                    label = 1 if final_return > 0 else -1

            labels.append(label)

        return labels

    # =========================================================================
    # Compliance Validation
    # =========================================================================

    def run_compliance_validation(
        self,
        results: List[Dict[str, Any]],
        count_parameters_helper,
        extract_walk_forward_helper,
    ) -> BacktestingComplianceResult:
        """
        Execute compliance validation on backtest results.

        COMPLIANCE: Validates rules R5, R6, R7, DATA-001:
        - R5: Walk-Forward Analysis (if WF results exist)
        - R6: Overfitting Prevention (ratio parameters/observations)
        - R7: Monte Carlo (if MC results exist)
        - DATA-001: Purged CV (if validation results exist)

        Args:
            results: List of backtest results
            count_parameters_helper: Helper to count optimizable parameters
            extract_walk_forward_helper: Helper to extract WF results

        Returns:
            BacktestingComplianceResult with validation result
        """
        logger.info("=" * 80)
        logger.info("COMPLIANCE VALIDATION (R5, R6, R7, DATA-001)")
        logger.info("=" * 80)

        n_parameters = count_parameters_helper()
        n_observations = len(self.quotes)

        walk_forward_windows = extract_walk_forward_helper(results)

        mc_results = [r for r in results if r.get('test_type') == 'monte_carlo']
        n_mc_simulations = len(mc_results)
        mc_var_95 = 0.0
        mc_var_99 = 0.0
        if mc_results:
            returns = [r.get('return_pct', 0) for r in mc_results]
            mc_var_95 = float(np.percentile(returns, 5)) if returns else 0.0
            mc_var_99 = float(np.percentile(returns, 1)) if returns else 0.0

        compliance_result = self.backtesting_compliance.validate_backtest(
            n_parameters=n_parameters,
            n_observations=n_observations,
            walk_forward_windows=walk_forward_windows,
            monte_carlo_var_95=mc_var_95,
            monte_carlo_var_99=mc_var_99,
            monte_carlo_simulations=n_mc_simulations,
            purge_days=5,
            embargo_days=10,
        )

        self.compliance_results.append(compliance_result)

        summary = compliance_result.get_summary()
        if compliance_result.is_compliant:
            logger.info(f"COMPLIANCE PASSED: {summary}")
        else:
            logger.warning(f"COMPLIANCE FAILED: {summary}")
            for violation in compliance_result.violations:
                logger.warning(f"  [{violation.severity}] {violation.rule_id}: {violation.message}")

        return compliance_result

    def count_optimizable_parameters(self) -> int:
        """
        Count optimizable parameters in configuration.

        Returns:
            Approximate number of optimizable parameters
        """
        count = 0

        modules = self.raw_config.get('modules', {})
        for _module_name, module_config in modules.items():
            if isinstance(module_config, dict):
                if 'thresholds' in module_config:
                    count += len(module_config['thresholds'])
                if 'parameters' in module_config:
                    count += len(module_config['parameters'])

        learning_engines = self.raw_config.get('learning_engines', {})
        for _engine_name, engine_config in learning_engines.items():
            if isinstance(engine_config, dict) and engine_config.get('enabled', False) and 'config' in engine_config:
                count += len(engine_config['config'])

        # Base backtest parameters
        count += 6

        return count

    def extract_walk_forward_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract walk-forward results for R5 validation.

        Args:
            results: List of backtest results

        Returns:
            List of results per walk-forward window
        """
        wf_results = [r for r in results if 'walk_forward' in r.get('test_type', '')]
        windows = []

        for r in wf_results:
            windows.append(
                {
                    'is_return': r.get('train_return', 0),
                    'oos_return': r.get('return_pct', 0),
                    'is_sharpe': r.get('train_sharpe', 0),
                    'oos_sharpe': r.get('sharpe_ratio', 0),
                    'trades': r.get('total_trades', 0),
                }
            )

        return windows

    def apply_meta_labeling(
        self,
        baseline_predictions: np.ndarray,
        optimized_predictions: np.ndarray,
        val_quotes: List,
    ) -> Dict[str, float]:
        """
        Apply meta-labeling from Lopez de Prado (rule 3).

        Meta-labeling uses ML to predict whether the primary signal was correct,
        enabling dynamic position sizing based on confidence.

        Args:
            baseline_predictions: Baseline model predictions
            optimized_predictions: Optimized model predictions
            val_quotes: Validation quotes

        Returns:
            Meta-labeling metrics
        """
        try:
            if len(baseline_predictions) == 0 or len(optimized_predictions) == 0:
                return {}

            meta_labels = (optimized_predictions > baseline_predictions).astype(int)

            meta_accuracy = meta_labels.mean() if len(meta_labels) > 0 else 0

            confidence_weights = optimized_predictions / (optimized_predictions.max() + 1e-8)
            weighted_performance = (meta_labels * confidence_weights).mean()

            return {
                'meta_accuracy': float(meta_accuracy),
                'weighted_performance': float(weighted_performance),
                'prediction_correlation': float(
                    np.corrcoef(baseline_predictions, optimized_predictions)[0, 1]
                    if len(baseline_predictions) > 1 and len(optimized_predictions) > 1
                    else 0
                ),
            }

        except Exception as e:
            logger.warning(f"Error applying meta-labeling: {e}")
            return {}
