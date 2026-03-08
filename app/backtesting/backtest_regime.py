"""
Backtest Regime Module - Regime-based backtest analysis.

Extracted from comprehensive_backtest_runner.py for Single Responsibility.
Handles regime-based backtest execution:
- Regime detection (HMM, Clustering, Simple)
- Per-regime performance analysis
- Regime transition analysis
- Robustness assessment

Architecture:
- Implements Lopez de Prado and Tsay regime analysis
- Supports multiple detection methods
- Markov chain transition analysis
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from app.backtesting.core.executor import SimpleBacktestExecutor
from app.backtesting.core.memory_manager import AggressiveMemoryManager
from app.backtesting.models import BacktestConfig
from app.domain.strategies.momentum_modular.strategy import ModularMomentumStrategy


class BacktestRegimeAnalyzer:
    """
    Handles regime-based backtest analysis.

    Provides methods for:
    - Regime detection (HMM, Clustering, Simple)
    - Per-regime performance analysis
    - Regime transition analysis
    - Strategy robustness assessment
    """

    def __init__(
        self,
        backtest_config: BacktestConfig,
        memory_manager: AggressiveMemoryManager,
        raw_config: Dict[str, Any],
        quotes: List,
    ):
        """
        Initialize BacktestRegimeAnalyzer.

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

    def run_regime_test_backtest(
        self,
        create_strategy_config_helper,
        strategy_name_helper,
        metrics_helper,
        audit_helper,
        thresholds_helper,
    ) -> List[Dict[str, Any]]:
        """
        Execute regime-based backtest to analyze strategy performance across market regimes.

        Implements advanced regime detection and analysis following:
        - Lopez de Prado (Rule 3): Structural change detection, regime-aware validation
        - Tsay (Rule 32): Time series regime switching models, stationarity testing
        - SRE (Rule 20): Performance degradation monitoring across regimes

        Architecture:
        1. Detect market regimes using multiple methods (HMM, Clustering, Correlation)
        2. Label each quote with its corresponding regime
        3. Execute backtests for each regime separately
        4. Calculate regime-specific metrics
        5. Perform regime transition analysis
        6. Identify regimes where strategy performs well/poorly

        Returns:
            List of dictionaries with regime-specific backtest results
        """
        logger.info("=" * 80)
        logger.info("REGIME TEST BACKTEST - Starting regime-based performance analysis")
        logger.info("=" * 80)

        try:
            # Step 1: Load configuration and prepare data
            regime_config = self.raw_config.get('backtests', {}).get('regime_test', {})

            detection_method = regime_config.get('detection_method', 'hmm')
            n_regimes = regime_config.get('n_regimes', 3)
            min_regime_samples = regime_config.get('min_regime_samples', 50)

            logger.info("Regime detection configuration:")
            logger.info(f"  Method: {detection_method}")
            logger.info(f"  Number of regimes: {n_regimes}")
            logger.info(f"  Minimum samples per regime: {min_regime_samples}")

            # Sort quotes by timestamp
            sorted_quotes = sorted(self.quotes, key=lambda x: x.timestamp)
            total_quotes = len(sorted_quotes)

            if total_quotes < 252:
                logger.error(f"Insufficient data for regime analysis: {total_quotes} < 252")
                return []

            logger.info(
                f"Data prepared: {total_quotes} quotes from {sorted_quotes[0].timestamp.date()} "
                f"to {sorted_quotes[-1].timestamp.date()}"
            )

            # Step 2: Prepare price data for regime detection
            prices = np.array([float(q.close) for q in sorted_quotes])
            returns = np.diff(prices) / prices[:-1]

            dates = pd.to_datetime([q.timestamp for q in sorted_quotes[1:]])
            returns_series = pd.Series(returns, index=dates)

            logger.info(f"Returns calculated: {len(returns)} observations")
            logger.info(f"  Mean return: {np.mean(returns):.6f}")
            logger.info(f"  Std return: {np.std(returns):.6f}")
            logger.info(f"  Annualized volatility: {np.std(returns) * np.sqrt(252):.4f}")

            # Step 3: Detect market regimes
            logger.info("\n" + "-" * 80)
            logger.info("REGIME DETECTION")
            logger.info("-" * 80)

            regime_labels = None
            regime_detector_info = {}

            # Method 1: HMM Regime Detection
            if detection_method in ['hmm', 'ensemble']:
                try:
                    from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
                        HMMRegimeDetector,
                    )

                    hmm_detector = HMMRegimeDetector(
                        config={'n_regimes': n_regimes, 'window_size': 100}
                    )

                    hmm_success = hmm_detector.fit(prices.tolist())

                    if hmm_success:
                        regime_predictions = []
                        for i in range(len(prices)):
                            window_prices = prices[max(0, i - 100) : i + 1]
                            pred = hmm_detector.detect(window_prices.tolist())
                            regime_predictions.append(pred.get('state', 1))

                        regime_labels = np.array(regime_predictions)
                        transition_matrix = hmm_detector.get_transition_matrix()
                        regime_means = hmm_detector.get_regime_means()

                        regime_detector_info['hmm'] = {
                            'used': True,
                            'transition_matrix': (
                                transition_matrix.tolist()
                                if transition_matrix is not None
                                else None
                            ),
                            'regime_means': (
                                regime_means.tolist() if regime_means is not None else None
                            ),
                        }
                        logger.info("HMM regime detection completed successfully")
                    else:
                        logger.warning("HMM training failed, falling back to clustering")
                        detection_method = 'clustering'

                except ImportError as e:
                    logger.error(f'HMM detector not available: {e}')
                    logger.info('Falling back to clustering regime detection')
                    detection_method = 'clustering'

            # Method 2: Clustering Regime Detection
            if detection_method in ['clustering', 'ensemble'] and regime_labels is None:
                try:
                    from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
                        ClusteringRegimeDetector,
                    )

                    cluster_detector = ClusteringRegimeDetector(
                        config={
                            'method': 'kmeans',
                            'n_clusters': n_regimes,
                            'window_size': 100,
                        }
                    )

                    cluster_success = cluster_detector.fit(prices.tolist())

                    if cluster_success:
                        regime_predictions = []
                        for i in range(len(prices)):
                            window_prices = prices[max(0, i - 100) : i + 1]
                            pred = cluster_detector.detect(window_prices.tolist())
                            regime_predictions.append(pred.get('cluster', 1))

                        regime_labels = np.array(regime_predictions)
                        regime_detector_info['clustering'] = {'used': True}
                        logger.info("Clustering regime detection completed successfully")
                    else:
                        logger.warning("Clustering training failed, using fallback")
                        regime_labels = np.ones(len(prices), dtype=int)

                except Exception as e:
                    logger.warning(f"Clustering detection error: {e}, using fallback")
                    regime_labels = np.ones(len(prices), dtype=int)

            # Fallback: Simple regime detection
            if regime_labels is None:
                logger.info("Using simple regime detection based on returns")
                regime_labels = self._detect_simple_regimes(returns)
                regime_detector_info['simple'] = {'used': True}

            # Align regime labels with returns
            regime_labels_returns = regime_labels[1:]

            # Map regime indices to names
            regime_names = self._get_regime_name_mapping(regime_labels_returns, returns_series)
            logger.info(f"Regime names mapped: {regime_names}")

            # Count samples per regime
            unique_regimes, regime_counts = np.unique(regime_labels_returns, return_counts=True)
            logger.info("Regime distribution:")
            for regime, count in zip(unique_regimes, regime_counts):
                regime_name = regime_names.get(regime, f"Regime_{regime}")
                pct = count / len(regime_labels_returns) * 100
                logger.info(f"  {regime_name}: {count} periods ({pct:.1f}%)")

            # Step 4: Analyze regime transitions
            logger.info("\n" + "-" * 80)
            logger.info("REGIME TRANSITION ANALYSIS")
            logger.info("-" * 80)

            transition_analysis = self._analyze_regime_transitions(
                regime_labels_returns, regime_names
            )

            logger.info("Regime transition probabilities:")
            for from_regime, transitions in transition_analysis.get(
                'transition_probabilities', {}
            ).items():
                logger.info(f"  From {from_regime}:")
                for to_regime, prob in transitions.items():
                    logger.info(f"    -> {to_regime}: {prob:.3f}")

            logger.info("Regime duration statistics:")
            for regime_name, stats in transition_analysis.get('duration_statistics', {}).items():
                logger.info(f"  {regime_name}:")
                logger.info(f"    Mean duration: {stats['mean_duration']:.1f} periods")
                logger.info(f"    Median duration: {stats['median_duration']:.1f} periods")
                logger.info(f"    Transitions: {stats['transitions']}")

            # Step 5: Execute backtests per regime
            logger.info("\n" + "-" * 80)
            logger.info("PER-REGIME BACKTESTING")
            logger.info("-" * 80)

            strategy_config = create_strategy_config_helper()
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

            regime_results = []
            regime_performance_summary = {}

            for regime_idx in unique_regimes:
                regime_name = regime_names.get(regime_idx, f"Regime_{regime_idx}")

                regime_mask = regime_labels_returns == regime_idx
                regime_quote_indices = np.where(regime_mask)[0] + 1

                if len(regime_quote_indices) < min_regime_samples:
                    logger.warning(
                        f"Skipping {regime_name}: insufficient samples "
                        f"({len(regime_quote_indices)} < {min_regime_samples})"
                    )
                    continue

                regime_quotes = [sorted_quotes[i] for i in regime_quote_indices]

                logger.info(f"\nTesting regime: {regime_name} ({len(regime_quotes)} quotes)")

                try:
                    result = executor.execute(
                        regime_quotes, strategy, strategy_name=f"{strategy_name}_{regime_name}"
                    )

                    consistent_metrics = metrics_helper(result, initial_capital)

                    regime_return_series = returns_series[regime_mask]
                    regime_volatility = float(regime_return_series.std() * np.sqrt(252))
                    regime_mean_return = float(regime_return_series.mean() * 252)

                    regime_result = {
                        'regime': regime_idx,
                        'regime_name': regime_name,
                        'num_quotes': len(regime_quotes),
                        'pct_total': len(regime_quotes) / len(sorted_quotes) * 100,
                        'total_pnl': consistent_metrics['total_pnl'],
                        'return_pct': consistent_metrics['return_pct'],
                        'sharpe_ratio': (
                            float(result.performance.sharpe_ratio)
                            if result.performance and result.performance.sharpe_ratio
                            else 0.0
                        ),
                        'sortino_ratio': (
                            float(result.performance.sortino_ratio)
                            if result.performance and hasattr(result.performance, 'sortino_ratio')
                            else 0.0
                        ),
                        'win_rate': (
                            float(result.performance.win_rate) if result.performance else 0.0
                        ),
                        'max_drawdown': (
                            float(result.performance.max_drawdown_percentage)
                            if result.performance
                            else 0.0
                        ),
                        'total_trades': (
                            result.performance.total_trades if result.performance else 0
                        ),
                        'avg_trade_pnl': (
                            consistent_metrics['total_pnl'] / result.performance.total_trades
                            if result.performance and result.performance.total_trades > 0
                            else 0.0
                        ),
                        'final_capital': consistent_metrics['final_capital'],
                        'regime_volatility': regime_volatility,
                        'regime_annualized_return': regime_mean_return,
                        'regime_sharpe': (
                            regime_mean_return / regime_volatility if regime_volatility > 0 else 0.0
                        ),
                    }

                    regime_results.append(regime_result)
                    regime_performance_summary[regime_name] = regime_result

                    logger.info(
                        f"  Results: Return={regime_result['return_pct']:.2f}%, "
                        f"Sharpe={regime_result['sharpe_ratio']:.3f}, "
                        f"Win Rate={regime_result['win_rate']:.2%}, "
                        f"Max DD={regime_result['max_drawdown']:.2f}%"
                    )

                    self.memory_manager.add_backtest_object(f'regime_{regime_name}', result)

                except Exception as e:
                    logger.error(f"Error backtesting regime {regime_name}: {e}", exc_info=True)
                    continue

            if not regime_results:
                logger.error("No regimes completed backtesting successfully")
                return []

            # Step 6: Calculate overall regime test statistics
            logger.info("\n" + "-" * 80)
            logger.info("REGIME ANALYSIS SUMMARY")
            logger.info("-" * 80)

            best_regime = max(regime_results, key=lambda x: x['sharpe_ratio'])
            worst_regime = min(regime_results, key=lambda x: x['sharpe_ratio'])

            logger.info(f"Best performing regime: {best_regime['regime_name']}")
            logger.info(f"  Sharpe: {best_regime['sharpe_ratio']:.3f}")
            logger.info(f"  Return: {best_regime['return_pct']:.2f}%")
            logger.info(f"  Win Rate: {best_regime['win_rate']:.2%}")

            logger.info(f"\nWorst performing regime: {worst_regime['regime_name']}")
            logger.info(f"  Sharpe: {worst_regime['sharpe_ratio']:.3f}")
            logger.info(f"  Return: {worst_regime['return_pct']:.2f}%")
            logger.info(f"  Win Rate: {worst_regime['win_rate']:.2%}")

            sharpe_values = [r['sharpe_ratio'] for r in regime_results]
            return_values = [r['return_pct'] for r in regime_results]

            sharpe_std = np.std(sharpe_values)
            sharpe_range = max(sharpe_values) - min(sharpe_values)
            return_std = np.std(return_values)

            robustness_score = 1.0 / (1.0 + sharpe_std)

            logger.info("\nRegime robustness metrics:")
            logger.info(f"  Sharpe std: {sharpe_std:.3f}")
            logger.info(f"  Sharpe range: {sharpe_range:.3f}")
            logger.info(f"  Return std: {return_std:.2f}%")
            logger.info(f"  Robustness score: {robustness_score:.3f}")

            # Step 7: Compile comprehensive results
            result_dict = {
                'test_type': 'regime_test',
                'test_name': 'Regime-Based Performance Analysis',
                'detection_method': detection_method,
                'n_regimes': n_regimes,
                'min_regime_samples': min_regime_samples,
                'regime_detector_info': regime_detector_info,
                'regime_names': regime_names,
                'regime_results': regime_results,
                'num_regimes_tested': len(regime_results),
                'best_regime': {
                    'name': best_regime['regime_name'],
                    'sharpe_ratio': float(best_regime['sharpe_ratio']),
                    'return_pct': float(best_regime['return_pct']),
                    'win_rate': float(best_regime['win_rate']),
                },
                'worst_regime': {
                    'name': worst_regime['regime_name'],
                    'sharpe_ratio': float(worst_regime['sharpe_ratio']),
                    'return_pct': float(worst_regime['return_pct']),
                    'win_rate': float(worst_regime['win_rate']),
                },
                'transition_analysis': transition_analysis,
                'robustness_metrics': {
                    'sharpe_std': float(sharpe_std),
                    'sharpe_range': float(sharpe_range),
                    'return_std': float(return_std),
                    'robustness_score': float(robustness_score),
                    'is_robust': robustness_score > 0.5,
                },
                'performance_summary': {
                    'avg_sharpe': float(np.mean(sharpe_values)),
                    'avg_return': float(np.mean(return_values)),
                    'avg_win_rate': float(np.mean([r['win_rate'] for r in regime_results])),
                    'avg_max_drawdown': float(np.mean([r['max_drawdown'] for r in regime_results])),
                    'total_trades': int(sum(r['total_trades'] for r in regime_results)),
                },
                'modules_active': (
                    list(self.raw_config['modules']['filters'].keys())
                    if 'modules' in self.raw_config
                    else []
                ),
                'learning_engine': None,
                'thresholds': thresholds_helper(strategy_config),
            }

            self.memory_manager.add_result(result_dict)
            audit_helper(result_dict, 'regime_test', strategy)

            logger.info("\n" + "=" * 80)
            logger.info("REGIME TEST BACKTEST COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Regimes tested: {len(regime_results)}")
            logger.info(f"Robustness score: {robustness_score:.3f}")
            logger.info(
                f"Best regime: {best_regime['regime_name']} (Sharpe={best_regime['sharpe_ratio']:.3f})"
            )
            logger.info(
                f"Worst regime: {worst_regime['regime_name']} (Sharpe={worst_regime['sharpe_ratio']:.3f})"
            )
            logger.info(
                f"Strategy is {'ROBUST' if robustness_score > 0.5 else 'SENSITIVE'} to regime changes"
            )
            logger.info("=" * 80)

            return [result_dict]

        except Exception as e:
            logger.error(f"Error in regime test backtest: {e}", exc_info=True)
            return []

    def _detect_simple_regimes(self, returns: np.ndarray) -> np.ndarray:
        """
        Simple regime detection based on returns and volatility.

        Fallback method when advanced detectors are unavailable.
        Classifies regimes based on return and volatility thresholds.

        Args:
            returns: Array of returns

        Returns:
            Array of regime labels (0=Bear, 1=Neutral, 2=Bull)
        """
        window = 20
        rolling_vol = pd.Series(returns).rolling(window).std().values
        rolling_ret = pd.Series(returns).rolling(window).mean().values

        vol_median = np.nanmedian(rolling_vol)
        ret_median = np.nanmedian(rolling_ret)

        regimes = np.ones(len(returns), dtype=int)  # Default to Neutral

        for i in range(len(returns)):
            vol = rolling_vol[i] if not np.isnan(rolling_vol[i]) else vol_median
            ret = rolling_ret[i] if not np.isnan(rolling_ret[i]) else ret_median

            if ret > ret_median * 1.5 and vol < vol_median * 1.2:
                regimes[i] = 2  # Bull: high return, low vol
            elif ret < ret_median * 0.5 and vol > vol_median * 1.2:
                regimes[i] = 0  # Bear: low return, high vol
            else:
                regimes[i] = 1  # Neutral

        return regimes

    def _get_regime_name_mapping(
        self, regime_labels: np.ndarray, returns: pd.Series
    ) -> Dict[int, str]:
        """
        Map regime indices to descriptive names based on characteristics.

        Args:
            regime_labels: Array of regime labels
            returns: Series of returns

        Returns:
            Dictionary mapping regime indices to names
        """
        unique_regimes = sorted(np.unique(regime_labels))
        regime_stats = {}

        for regime in unique_regimes:
            mask = regime_labels == regime
            regime_returns = returns[mask]

            regime_stats[regime] = {
                'mean_return': float(regime_returns.mean()),
                'volatility': float(regime_returns.std()),
            }

        sorted_regimes = sorted(regime_stats.items(), key=lambda x: x[1]['mean_return'])

        regime_names = {}
        if len(sorted_regimes) == 3:
            regime_names[sorted_regimes[0][0]] = 'Bear Market'
            regime_names[sorted_regimes[1][0]] = 'Neutral Market'
            regime_names[sorted_regimes[2][0]] = 'Bull Market'
        elif len(sorted_regimes) == 2:
            regime_names[sorted_regimes[0][0]] = 'Bear Market'
            regime_names[sorted_regimes[1][0]] = 'Bull Market'
        else:
            for regime, stats in sorted_regimes:
                if stats['mean_return'] > 0:
                    regime_names[regime] = f'Positive_Regime_{regime}'
                else:
                    regime_names[regime] = f'Negative_Regime_{regime}'

        return regime_names

    def _analyze_regime_transitions(
        self, regime_labels: np.ndarray, regime_names: Dict[int, str]
    ) -> Dict[str, Any]:
        """
        Analyze regime transitions and build transition probability matrix.

        Implements Markov chain analysis for regime switching (Tsay).

        Args:
            regime_labels: Array of regime labels
            regime_names: Mapping of regime indices to names

        Returns:
            Dictionary with transition analysis results
        """
        unique_regimes = sorted(np.unique(regime_labels))
        n_regimes = len(unique_regimes)

        # Build transition matrix
        transition_matrix = np.zeros((n_regimes, n_regimes))
        for i in range(len(regime_labels) - 1):
            from_regime = regime_labels[i]
            to_regime = regime_labels[i + 1]
            from_idx = unique_regimes.index(from_regime)
            to_idx = unique_regimes.index(to_regime)
            transition_matrix[from_idx, to_idx] += 1

        # Normalize to get probabilities
        transition_probs = transition_matrix.copy()
        for i in range(n_regimes):
            row_sum = transition_matrix[i, :].sum()
            if row_sum > 0:
                transition_probs[i, :] /= row_sum

        # Build named transition matrix
        named_transition_probs = {}
        for i, from_regime in enumerate(unique_regimes):
            from_name = regime_names.get(from_regime, f"Regime_{from_regime}")
            named_transition_probs[from_name] = {}
            for j, to_regime in enumerate(unique_regimes):
                to_name = regime_names.get(to_regime, f"Regime_{to_regime}")
                named_transition_probs[from_name][to_name] = float(transition_probs[i, j])

        # Analyze regime durations
        regime_durations = {name: [] for name in regime_names.values()}
        current_regime = regime_labels[0]
        current_duration = 1

        for i in range(1, len(regime_labels)):
            if regime_labels[i] == current_regime:
                current_duration += 1
            else:
                regime_name = regime_names.get(current_regime, f"Regime_{current_regime}")
                if regime_name in regime_durations:
                    regime_durations[regime_name].append(current_duration)
                current_regime = regime_labels[i]
                current_duration = 1

        # Add last regime duration
        regime_name = regime_names.get(current_regime, f"Regime_{current_regime}")
        if regime_name in regime_durations:
            regime_durations[regime_name].append(current_duration)

        # Calculate duration statistics
        duration_stats = {}
        for regime_name, durations in regime_durations.items():
            if durations:
                duration_stats[regime_name] = {
                    'mean_duration': float(np.mean(durations)),
                    'median_duration': float(np.median(durations)),
                    'min_duration': int(np.min(durations)),
                    'max_duration': int(np.max(durations)),
                    'std_duration': float(np.std(durations)),
                    'transitions': int(len(durations)),
                }

        return {
            'transition_matrix': transition_matrix.tolist(),
            'transition_probabilities': named_transition_probs,
            'duration_statistics': duration_stats,
        }
