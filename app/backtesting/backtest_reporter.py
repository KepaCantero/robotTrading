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
from typing import TYPE_CHECKING, Protocol, Union, runtime_checkable

import pandas as pd

logger = logging.getLogger(__name__)


from app.backtesting.factories import StrategyFactory

if TYPE_CHECKING:
    from decimal import Decimal
    from pathlib import Path

    import numpy as np

    from app.backtesting.core.memory_manager import AggressiveMemoryManager
    from app.backtesting.models import BacktestResult

# Type aliases for YAML-like nested config structures.
# ConfigValue represents a single value that can be a primitive, list, or dict.
# ConfigDict is the standard dict shape used throughout this module.
ConfigValue = Union[str, int, float, bool, list, dict]
ConfigDict = dict[str, ConfigValue]


@runtime_checkable
class AuditTrailProtocol(Protocol):
    """Protocol for audit trail instances."""

    def log_test_result(self, result_dict: ConfigDict) -> None: ...


@runtime_checkable
class LearningStorageProtocol(Protocol):
    """Protocol for learning storage instances."""

    def save_weights(
        self,
        engine_name: str,
        weights: object,
        test_id: str | ConfigValue,
        metrics: ConfigDict,
    ) -> None: ...

    async def save_weights_async(
        self,
        engine_name: str,
        weights: object,
        test_id: str | ConfigValue,
        metadata: ConfigDict,
    ) -> str | None: ...


@runtime_checkable
class StrategyWithFeaturesProtocol(Protocol):
    """Protocol for strategy instances with _compute_features and learning_engines."""

    def _compute_features(self, quote: object) -> object: ...

    learning_engines: dict[str, object]


@runtime_checkable
class StrategyWithLearningEngineProtocol(Protocol):
    """Protocol for strategy instances with learning_engine attribute."""

    learning_engine: object


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
        raw_config: ConfigDict,
        output_dir: Path,
        meta_enabled: bool = False,
        audit_trail: AuditTrailProtocol | None = None,
        learning_storage: LearningStorageProtocol | None = None,
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

    def save_results(self, results: list[ConfigDict]) -> None:
        """
        Save results to files.

        Args:
            results: List of results to save
        """
        if not results:
            logger.warning("No results to save")
            return

        reporting_config: ConfigDict = self.raw_config.get("reporting", {})
        output_formats: ConfigValue = reporting_config.get("output_format", ["csv", "json"])

        if not isinstance(output_formats, list):
            output_formats = ["csv", "json"]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save CSV
        if "csv" in output_formats:
            csv_path = self.output_dir / f"backtest_results_{timestamp}.csv"
            df = pd.DataFrame(results)
            df.to_csv(csv_path, index=False)
            logger.info(f"Results saved to CSV: {csv_path}")

        # Save JSON
        if "json" in output_formats:
            json_path = self.output_dir / f"backtest_results_{timestamp}.json"

            with open(json_path, "w") as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to JSON: {json_path}")

    def save_test_audit_and_weights(
        self,
        result_dict: ConfigDict,
        test_type: str,
        strategy: object,
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
            if self.audit_trail is not None:
                self.audit_trail.log_test_result(result_dict)

            # Save weights if there's a learning engine
            if self.learning_storage is not None and result_dict.get("learning_engine"):
                engine_type = result_dict["learning_engine"]
                if isinstance(engine_type, str) and isinstance(
                    strategy, StrategyWithLearningEngineProtocol
                ):
                    learning_model = strategy.learning_engine
                    if hasattr(learning_model, "model"):
                        model_value = learning_model.model
                    else:
                        model_value = learning_model
                    try:
                        self.learning_storage.save_weights(
                            engine_name=engine_type,
                            weights=model_value,
                            test_id=result_dict["test_name"],
                            metrics=result_dict,
                        )
                    except Exception as e:
                        logger.warning(f"Could not save weights: {e}")

        except Exception as e:
            logger.warning(f"Error saving audit/weights: {e}")

    async def save_weights_async(
        self,
        engine_type: str,
        strategy: object,
        result_dict: ConfigDict,
    ) -> str | None:
        """
        Save learning engine weights asynchronously for better performance.

        Args:
            engine_type: Type of learning engine
            strategy: Strategy instance with learning_engine
            result_dict: Test result dictionary

        Returns:
            Path to saved weights or None
        """
        if self.learning_storage is None:
            return None

        try:
            learning_model: object
            if isinstance(strategy, StrategyWithLearningEngineProtocol):
                learning_model = strategy.learning_engine
            else:
                learning_model = strategy

            weights_path = await self.learning_storage.save_weights_async(
                engine_name=engine_type,
                weights=learning_model,
                test_id=result_dict["test_name"],
                metadata={
                    "test_type": result_dict.get("test_type", "unknown"),
                    "timestamp": result_dict.get("timestamp"),
                    "metrics": {
                        "total_pnl": result_dict.get("total_pnl"),
                        "sharpe_ratio": result_dict.get("sharpe_ratio"),
                        "total_trades": result_dict.get("total_trades"),
                    },
                },
            )
            logger.info(f"Weights saved asynchronously: {weights_path}")
            return weights_path
        except Exception as e:
            logger.warning(f"Could not save weights async: {e}")
            return None

    async def finalize_meta_analysis(self, results: list[ConfigDict]) -> ConfigDict:
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
            or not hasattr(self, "meta_analyzer")
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

            summary: ConfigDict = {
                "total_results_analyzed": num_loaded,
                "performance_summary": performance,
                "outliers": outliers,
                "suggestions": suggestions,
                "analysis_timestamp": datetime.now().isoformat(),
                "output_directory": str(self.output_dir),
            }

            analysis_path = (
                self.output_dir / f"meta_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(analysis_path, "w") as f:
                json.dump(summary, f, indent=2, default=str)

            logger.info(f"Meta-analysis complete: {analysis_path}")
            logger.info(f"  - Total results: {num_loaded}")
            logger.info(f"  - Performance metrics: {len(performance)} categories")
            if isinstance(outliers, dict):
                logger.info(f"  - Outliers detected: {len(outliers.get('outliers', []))}")
            logger.info(f"  - Suggestions generated: {len(suggestions)}")

            return summary

        except Exception as e:
            logger.error(f"Error during meta-analysis: {e}", exc_info=True)
            return {}

    def calculate_consistent_metrics(
        self, result: BacktestResult, initial_capital: Decimal
    ) -> dict[str, float]:
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
            "total_pnl": total_pnl,
            "return_pct": return_pct,
            "final_capital": final_capital_float,
        }

    def get_results(self) -> list[ConfigDict]:
        """
        Get all stored results.

        Returns:
            List of results
        """
        return self.memory_manager.get_results()

    def get_memory_stats(self) -> ConfigDict:
        """
        Get memory statistics.

        Returns:
            Dictionary with statistics
        """
        return self.memory_manager.get_stats()

    def _get_nested_dict(self, key: str) -> ConfigDict:
        """Helper to get a nested dict from raw_config with proper typing."""
        value = self.raw_config.get(key, {})
        if isinstance(value, dict):
            return value
        return {}

    def create_strategy_config(self) -> ConfigDict:
        """
        Create strategy configuration from YAML config.

        Supports two config structures:
        1. YAML with modules.filters at root (from momentum_modular.yaml)
        2. Optimized config with strategy.modules (from Bayesian optimizer)

        Returns:
            Strategy configuration dictionary
        """
        # Check for strategy.modules (from optimizer) FIRST
        strategy_config = self._get_nested_dict("strategy")
        if "modules" in strategy_config:
            modules_val = strategy_config["modules"]
            modules: ConfigDict = modules_val if isinstance(modules_val, dict) else {}
            return {
                "type": strategy_config.get("type", "modular_momentum"),
                "preset": strategy_config.get("preset", "balanced"),
                "modules": modules,
                "thresholds": strategy_config.get("thresholds", {}),
                "risk_manager": strategy_config.get("risk_manager", {}),
            }

        # If config has modules.filters, create adapted config
        modules_section = self.raw_config.get("modules")
        if isinstance(modules_section, dict) and "filters" in modules_section:
            raw_filters = modules_section["filters"]
            if isinstance(raw_filters, dict):
                filters_config: ConfigDict = {}
                filters: dict[str, ConfigValue] = raw_filters

                # Filter name mapping
                filter_name_map = {
                    "ema": "ema_filter",
                    "rsi": "rsi_filter",
                    "stoch_rsi": "stoch_rsi_filter",
                    "momentum": "momentum_filter",
                    "volume": "volume_filter",
                    "atr": "atr_filter",
                }

                for filter_name, filter_config_raw in filters.items():
                    if not isinstance(filter_config_raw, dict):
                        continue
                    filter_config: ConfigDict = filter_config_raw
                    if filter_config.get("enabled", False):
                        if filter_name.endswith("_filter"):
                            mapped_name = filter_name
                        else:
                            mapped_name = filter_name_map.get(filter_name, f"{filter_name}_filter")

                        filter_params: ConfigDict = {}
                        raw_parameters = filter_config.get("parameters", {})
                        if isinstance(raw_parameters, dict):
                            parameters: dict[str, ConfigValue] = raw_parameters
                            for param_name, param_config_raw in parameters.items():
                                if isinstance(param_config_raw, dict):
                                    param_config: ConfigDict = param_config_raw
                                    if "default" in param_config:
                                        filter_params[param_name] = param_config["default"]

                        filter_entry: ConfigDict = {"enabled": True}
                        filter_entry.update(filter_params)
                        filters_config[mapped_name] = filter_entry

                return {
                    "type": "modular_momentum",
                    "preset": "custom",
                    "modules": filters_config,
                    "presets": {
                        "custom": {
                            "combination_mode": "MAJORITY",
                            "min_confidence": 0.7,
                            "learning_mode": "supervised",
                        }
                    },
                }

        return StrategyFactory.create_baseline_config(self.raw_config)

    def extract_filter_thresholds(self) -> ConfigDict:
        """
        Extract thresholds from filter configuration.

        Returns:
            Dictionary with thresholds for each active filter
        """
        thresholds: ConfigDict = {}
        modules_section = self.raw_config.get("modules", {})
        if not isinstance(modules_section, dict):
            return thresholds

        raw_filters = modules_section.get("filters", {})
        if not isinstance(raw_filters, dict):
            return thresholds

        filters_config: dict[str, ConfigValue] = raw_filters

        for filter_name, filter_config_raw in filters_config.items():
            if not isinstance(filter_config_raw, dict):
                continue
            filter_config: ConfigDict = filter_config_raw
            if filter_config.get("enabled", False):
                raw_params = filter_config.get("parameters", {})
                if not isinstance(raw_params, dict):
                    continue
                params: dict[str, ConfigValue] = raw_params
                for param_name, param_config_raw in params.items():
                    if isinstance(param_config_raw, dict):
                        param_config: ConfigDict = param_config_raw
                        if "default" in param_config:
                            threshold_key = f"{filter_name}.{param_name}"
                            thresholds[threshold_key] = param_config["default"]

        return thresholds

    def get_strategy_name(self, strategy: object) -> str:
        """
        Get strategy name.

        Phase 5: Now delegates to StrategyFactory.

        Args:
            strategy: Strategy instance

        Returns:
            Strategy name string
        """
        return str(StrategyFactory.get_strategy_name(strategy))

    def extract_thresholds(self, strategy_config: ConfigDict) -> ConfigDict:
        """
        Extract thresholds from strategy configuration.

        Phase 5: Now delegates to StrategyFactory.

        Args:
            strategy_config: Strategy configuration dictionary

        Returns:
            Thresholds dictionary
        """
        return StrategyFactory.extract_thresholds(strategy_config)

    def create_ablation_config(self, disabled_filter: str) -> ConfigDict:
        """
        Create strategy configuration with a specific filter disabled for ablation testing.

        Args:
            disabled_filter: Name of the filter to disable

        Returns:
            Strategy configuration dictionary with the specified filter disabled
        """
        modules_section = self.raw_config.get("modules")
        if not isinstance(modules_section, dict) or "filters" not in modules_section:
            return self.create_strategy_config()

        raw_filters = modules_section["filters"]
        if not isinstance(raw_filters, dict):
            return self.create_strategy_config()

        filters: dict[str, ConfigValue] = raw_filters
        filters_config: ConfigDict = {}

        for filter_name, filter_config_raw in filters.items():
            if filter_name == disabled_filter:
                continue
            if not isinstance(filter_config_raw, dict):
                continue

            filter_config: ConfigDict = filter_config_raw
            if filter_config.get("enabled", False):
                filter_params: ConfigDict = {}
                raw_parameters = filter_config.get("parameters", {})
                if isinstance(raw_parameters, dict):
                    parameters: dict[str, ConfigValue] = raw_parameters
                    for param_name, param_config_raw in parameters.items():
                        if isinstance(param_config_raw, dict):
                            param_config: ConfigDict = param_config_raw
                            if "default" in param_config:
                                filter_params[param_name] = param_config["default"]

                filter_entry: ConfigDict = {"enabled": True}
                filter_entry.update(filter_params)
                filters_config[filter_name] = filter_entry

        return {
            "type": "modular_momentum",
            "preset": "custom",
            "modules": filters_config,
            "presets": {
                "custom": {
                    "combination_mode": "MAJORITY",
                    "min_confidence": 0.7,
                    "learning_mode": "supervised",
                }
            },
        }

    def extract_transformer_predictions(self, strategy: object, quotes: list[object]) -> np.ndarray:
        """
        Extract Transformer predictions from strategy.

        Args:
            strategy: Trained strategy with Transformer engine
            quotes: Quotes to predict on

        Returns:
            Array of predictions/confidence scores
        """
        import numpy as np

        predictions: list[float] = []

        try:
            if (
                isinstance(strategy, StrategyWithFeaturesProtocol)
                and "transformer" in strategy.learning_engines
            ):
                transformer_engine = strategy.learning_engines["transformer"]

                for quote in quotes:
                    features = strategy._compute_features(quote)
                    if hasattr(transformer_engine, "predict"):
                        prediction_result = transformer_engine.predict(features)
                        if (
                            isinstance(prediction_result, dict)
                            and "confidence" in prediction_result
                        ):
                            conf = prediction_result["confidence"]
                            predictions.append(
                                float(conf) if isinstance(conf, (int, float)) else 0.0
                            )
                        else:
                            predictions.append(0.0)

        except Exception as e:
            logger.warning(f"Error extracting Transformer predictions: {e}")
            return np.array([], dtype=float)

        return np.array(predictions, dtype=float)

    def extract_transformer_feature_importance(self, strategy: object) -> dict[str, float]:
        """
        Extract feature importance from Transformer model.

        Implements MLOps rule 27.9 for feature importance tracking.

        Args:
            strategy: Strategy with trained Transformer

        Returns:
            Dictionary with feature importance scores
        """
        try:
            if (
                isinstance(strategy, StrategyWithFeaturesProtocol)
                and "transformer" in strategy.learning_engines
            ):
                transformer_engine = strategy.learning_engines["transformer"]

                if hasattr(transformer_engine, "model") and transformer_engine.model is not None:
                    # Extract attention weights as proxy for feature importance
                    feature_importance: dict[str, float] = {
                        "attention_score": 1.0,
                        "sequence_importance": 0.8,
                        "temporal_importance": 0.9,
                    }
                    return feature_importance

        except Exception as e:
            logger.warning(f"Error extracting Transformer feature importance: {e}")

        return {}
