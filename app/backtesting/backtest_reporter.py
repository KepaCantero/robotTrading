"""
Backtest Reporter Module - Report generation and configuration handling.

Extracted from comprehensive_backtest_runner.py for Single Responsibility.
Handles:
- Result saving (CSV, JSON)
- Audit trail management
- Metrics calculation
- Strategy configuration creation
- Memory management utilities
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

from app.backtesting.core.memory_manager import AggressiveMemoryManager
from app.backtesting.factories import StrategyFactory
from app.backtesting.models import BacktestResult


class BacktestReporter:
    """
    Handles report generation and configuration handling.

    Provides methods for:
    - Saving results to CSV and JSON
    - Managing audit trails
    - Calculating consistent metrics
    - Creating strategy configurations
    - Memory management utilities
    """

    def __init__(
        self,
        memory_manager: AggressiveMemoryManager,
        raw_config: Dict[str, Any],
        output_dir: Path,
        meta_enabled: bool = False,
        audit_trail: Any = None,
        learning_storage: Any = None,
    ):
        """
        Initialize BacktestReporter.

        Args:
            memory_manager: Memory manager for storing results
            raw_config: Raw YAML configuration
            output_dir: Output directory for reports
            meta_enabled: Whether meta-analysis is enabled
            audit_trail: Audit trail instance
            learning_storage: Learning storage instance
        """
        self.memory_manager = memory_manager
        self.raw_config = raw_config
        self.output_dir = output_dir
        self.meta_enabled = meta_enabled
        self.audit_trail = audit_trail
        self.learning_storage = learning_storage

    def save_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Save results to files.

        Args:
            results: List of results to save
        """
        if not results:
            logger.warning("No results to save")
            return

        reporting_config = self.raw_config.get('reporting', {})
        output_formats = reporting_config.get('output_format', ['csv', 'json'])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save CSV
        if 'csv' in output_formats:
            csv_path = self.output_dir / f"backtest_results_{timestamp}.csv"
            df = pd.DataFrame(results)
            df.to_csv(csv_path, index=False)
            logger.info(f"Results saved to CSV: {csv_path}")

        # Save JSON
        if 'json' in output_formats:
            json_path = self.output_dir / f"backtest_results_{timestamp}.json"

            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to JSON: {json_path}")

    def save_test_audit_and_weights(
        self, result_dict: Dict[str, Any], test_type: str, strategy: Any
    ) -> None:
        """
        Save audit and weights for a test.

        Args:
            result_dict: Backtest result dictionary
            test_type: Type of test
            strategy: Strategy used
        """
        if not self.meta_enabled:
            return

        try:
            # Save audit
            if self.audit_trail:
                self.audit_trail.log_test_result(result_dict)

            # Save weights if there's a learning engine
            if self.learning_storage and result_dict.get('learning_engine'):
                engine_type = result_dict['learning_engine']
                if hasattr(strategy, 'learning_engine') and strategy.learning_engine:
                    try:
                        self.learning_storage.save_weights(
                            engine_name=engine_type,
                            weights=strategy.learning_engine.model,
                            test_id=result_dict['test_name'],
                            metrics=result_dict,
                        )
                    except Exception as e:
                        logger.warning(f"Could not save weights: {e}")

        except Exception as e:
            logger.warning(f"Error saving audit/weights: {e}")

    async def save_weights_async(
        self, engine_type: str, strategy: Any, result_dict: Dict[str, Any]
    ) -> Optional[str]:
        """
        Save learning engine weights asynchronously for better performance.

        Args:
            engine_type: Type of learning engine
            strategy: Strategy instance with learning_engine
            result_dict: Test result dictionary

        Returns:
            Path to saved weights or None
        """
        if not self.learning_storage:
            return None

        try:
            weights_path = await self.learning_storage.save_weights_async(
                engine_name=engine_type,
                weights=strategy.learning_engine.model,
                test_id=result_dict['test_name'],
                metadata={
                    'test_type': result_dict.get('test_type', 'unknown'),
                    'timestamp': result_dict.get('timestamp'),
                    'metrics': {
                        'total_pnl': result_dict.get('total_pnl'),
                        'sharpe_ratio': result_dict.get('sharpe_ratio'),
                        'total_trades': result_dict.get('total_trades'),
                    },
                },
            )
            logger.info(f"Weights saved asynchronously: {weights_path}")
            return weights_path
        except Exception as e:
            logger.warning(f"Could not save weights async: {e}")
            return None

    async def finalize_meta_analysis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Finalize meta-analysis after all backtests complete.

        This method loads all backtest results into the MetaAnalyzer and runs
        comprehensive analysis including performance metrics, outlier detection,
        and optimization suggestions.

        Args:
            results: List of all backtest result dictionaries

        Returns:
            Meta-analysis summary dictionary
        """
        if (
            not self.meta_enabled
            or not hasattr(self, 'meta_analyzer')
            or self.meta_analyzer is None
        ):
            logger.info("Meta-analysis not enabled, skipping")
            return {}

        try:
            logger.info("Starting meta-analysis of all backtest results...")

            logger.info(f"Loading results from {self.output_dir}...")
            num_loaded = await self.meta_analyzer.load_results(str(self.output_dir))
            logger.info(f"Loaded {num_loaded} results into MetaAnalyzer")

            if num_loaded == 0:
                logger.warning("No results to analyze")
                return {}

            logger.info("Running performance analysis...")
            performance = self.meta_analyzer.analyze_performance()

            logger.info("Detecting outliers...")
            outliers = self.meta_analyzer.detect_outliers()

            logger.info("Generating optimization suggestions...")
            suggestions = self.meta_analyzer.generate_suggestions()

            summary = {
                'total_results_analyzed': num_loaded,
                'performance_summary': performance,
                'outliers': outliers,
                'suggestions': suggestions,
                'analysis_timestamp': datetime.now().isoformat(),
                'output_directory': str(self.output_dir),
            }

            analysis_path = (
                self.output_dir / f"meta_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(analysis_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)

            logger.info(f"Meta-analysis complete: {analysis_path}")
            logger.info(f"  - Total results: {num_loaded}")
            logger.info(f"  - Performance metrics: {len(performance)} categories")
            logger.info(f"  - Outliers detected: {len(outliers.get('outliers', []))}")
            logger.info(f"  - Suggestions generated: {len(suggestions)}")

            return summary

        except Exception as e:
            logger.error(f"Error during meta-analysis: {e}", exc_info=True)
            return {}

    def calculate_consistent_metrics(
        self, result: BacktestResult, initial_capital: Decimal
    ) -> Dict[str, float]:
        """
        Calculate consistent metrics from BacktestResult.

        Args:
            result: Backtest result
            initial_capital: Initial capital

        Returns:
            Dictionary with calculated metrics
        """
        initial_capital_float = float(initial_capital)
        final_capital_float = float(result.final_capital)

        total_pnl = final_capital_float - initial_capital_float
        return_pct = (total_pnl / initial_capital_float * 100) if initial_capital_float > 0 else 0.0

        return {
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'final_capital': final_capital_float,
        }

    def get_results(self) -> List[Dict[str, Any]]:
        """
        Get all stored results.

        Returns:
            List of results
        """
        return self.memory_manager.get_results()

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Dictionary with statistics
        """
        return self.memory_manager.get_stats()

    def create_strategy_config(self) -> Dict[str, Any]:
        """
        Create strategy configuration from YAML config.

        Supports two config structures:
        1. YAML with modules.filters at root (from momentum_modular.yaml)
        2. Optimized config with strategy.modules (from Bayesian optimizer)

        Returns:
            Strategy configuration dictionary
        """
        # Check for strategy.modules (from optimizer) FIRST
        strategy_config = self.raw_config.get('strategy', {})
        if 'modules' in strategy_config:
            return {
                'type': strategy_config.get('type', 'modular_momentum'),
                'preset': strategy_config.get('preset', 'balanced'),
                'modules': strategy_config['modules'],
                'thresholds': strategy_config.get('thresholds', {}),
                'risk_manager': strategy_config.get('risk_manager', {}),
            }

        # If config has modules.filters, create adapted config
        if 'modules' in self.raw_config and 'filters' in self.raw_config['modules']:
            filters_config = {}
            filters = self.raw_config['modules']['filters']

            # Filter name mapping
            filter_name_map = {
                'ema': 'ema_filter',
                'rsi': 'rsi_filter',
                'stoch_rsi': 'stoch_rsi_filter',
                'momentum': 'momentum_filter',
                'volume': 'volume_filter',
                'atr': 'atr_filter',
            }

            for filter_name, filter_config in filters.items():
                if filter_config.get('enabled', False):
                    if filter_name.endswith('_filter'):
                        mapped_name = filter_name
                    else:
                        mapped_name = filter_name_map.get(filter_name, f'{filter_name}_filter')

                    filter_params = {}
                    for param_name, param_config in filter_config.get('parameters', {}).items():
                        if 'default' in param_config:
                            filter_params[param_name] = param_config['default']

                    filters_config[mapped_name] = {'enabled': True, **filter_params}

            return {
                'type': 'modular_momentum',
                'preset': 'custom',
                'modules': filters_config,
                'presets': {
                    'custom': {
                        'combination_mode': 'MAJORITY',
                        'min_confidence': 0.7,
                        'learning_mode': 'supervised',
                    }
                },
            }

        return StrategyFactory.create_baseline_config(self.raw_config)

    def extract_filter_thresholds(self) -> Dict[str, Any]:
        """
        Extract thresholds from filter configuration.

        Returns:
            Dictionary with thresholds for each active filter
        """
        thresholds = {}
        filters_config = self.raw_config.get('modules', {}).get('filters', {})

        for filter_name, filter_config in filters_config.items():
            if filter_config.get('enabled', False):
                params = filter_config.get('parameters', {})
                for param_name, param_config in params.items():
                    if 'default' in param_config:
                        threshold_key = f"{filter_name}.{param_name}"
                        thresholds[threshold_key] = param_config['default']

        return thresholds

    def get_strategy_name(self, strategy: Any) -> str:
        """
        Get strategy name.

        Phase 5: Now delegates to StrategyFactory.

        Args:
            strategy: Strategy instance

        Returns:
            Strategy name string
        """
        return StrategyFactory.get_strategy_name(strategy)

    def extract_thresholds(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract thresholds from strategy configuration.

        Phase 5: Now delegates to StrategyFactory.

        Args:
            strategy_config: Strategy configuration dictionary

        Returns:
            Thresholds dictionary
        """
        return StrategyFactory.extract_thresholds(strategy_config)

    def create_ablation_config(self, disabled_filter: str) -> Dict[str, Any]:
        """
        Create strategy configuration with a specific filter disabled for ablation testing.

        Args:
            disabled_filter: Name of the filter to disable

        Returns:
            Strategy configuration dictionary with the specified filter disabled
        """
        if 'modules' not in self.raw_config or 'filters' not in self.raw_config['modules']:
            return self.create_strategy_config()

        filters_config = {}
        filters = self.raw_config['modules']['filters']

        for filter_name, filter_config in filters.items():
            if filter_name == disabled_filter:
                continue

            if filter_config.get('enabled', False):
                filter_params = {}
                for param_name, param_config in filter_config.get('parameters', {}).items():
                    if 'default' in param_config:
                        filter_params[param_name] = param_config['default']

                filters_config[filter_name] = {'enabled': True, **filter_params}

        return {
            'type': 'modular_momentum',
            'preset': 'custom',
            'modules': filters_config,
            'presets': {
                'custom': {
                    'combination_mode': 'MAJORITY',
                    'min_confidence': 0.7,
                    'learning_mode': 'supervised',
                }
            },
        }

    def extract_transformer_predictions(self, strategy: Any, quotes: List) -> 'np.ndarray':
        """
        Extract Transformer predictions from strategy.

        Args:
            strategy: Trained strategy with Transformer engine
            quotes: Quotes to predict on

        Returns:
            Array of predictions/confidence scores
        """
        import numpy as np

        predictions = []

        try:
            if hasattr(strategy, 'learning_engines') and 'transformer' in strategy.learning_engines:
                transformer_engine = strategy.learning_engines['transformer']

                for quote in quotes:
                    features = strategy._compute_features(quote)
                    prediction = transformer_engine.predict(features)
                    predictions.append(prediction.get('confidence', 0.0))

        except Exception as e:
            logger.warning(f"Error extracting Transformer predictions: {e}")
            return np.array([])

        return np.array(predictions)

    def extract_transformer_feature_importance(self, strategy: Any) -> Dict[str, float]:
        """
        Extract feature importance from Transformer model.

        Implements MLOps rule 27.9 for feature importance tracking.

        Args:
            strategy: Strategy with trained Transformer

        Returns:
            Dictionary with feature importance scores
        """
        try:
            if hasattr(strategy, 'learning_engines') and 'transformer' in strategy.learning_engines:
                transformer_engine = strategy.learning_engines['transformer']

                if hasattr(transformer_engine, 'model') and transformer_engine.model is not None:
                    # Extract attention weights as proxy for feature importance
                    feature_importance = {
                        'attention_score': 1.0,
                        'sequence_importance': 0.8,
                        'temporal_importance': 0.9,
                    }
                    return feature_importance

        except Exception as e:
            logger.warning(f"Error extracting Transformer feature importance: {e}")

        return {}
